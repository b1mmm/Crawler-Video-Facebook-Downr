import json
import time
import sys
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

# ========== CONFIG ==========
DOWNR = "https://downr.org/"
TARGET_SUBSTR = "/.netlify/functions/nyt"

INPUT_FILE = "input.txt"
RAW_JS_FILE = "raw_list.js"

INPUT_XPATH = "//input[@placeholder='Paste URL here']"
BTN_XPATH = "//button[normalize-space()='Download']"

# Nếu bạn vẫn muốn in FINAL VIDEO thì giữ hàm pick_best_video_url (dùng medias).
# Nếu không cần, có thể bỏ.
def pick_best_video_url(resp_json):
    medias = resp_json.get("medias", []) or []
    video = next(
        (m for m in medias if m.get("type") == "video" and m.get("quality") == "HD"),
        next((m for m in medias if m.get("type") == "video" and m.get("quality") == "SD"), None),
    )
    return (video.get("url"), video.get("quality")) if video else (None, None)

# ========== IO ==========
def read_urls(path: str) -> List[str]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Không thấy file: {path}")

    urls = []
    for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        urls.append(line)
    return urls

def append_to_raw_list_js(url, path=RAW_JS_FILE) -> Tuple[bool, int]:
    """
    Append input_url vào raw_list.js theo format:
    const RAW_LIST = [
      "url1",
      ...
    ];
    Tránh trùng.
    """
    p = Path(path)
    if not p.exists():
        p.write_text("const RAW_LIST = [\n];", encoding="utf-8")

    text = p.read_text(encoding="utf-8")
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("raw_list.js format invalid")

    body = text[start + 1 : end].strip()

    existing = []
    if body:
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith('"') and line.endswith('"'):
                existing.append(line.strip('"'))

    if url in existing:
        return False, len(existing)

    existing.append(url)

    new_js = "const RAW_LIST = [\n"
    for u in existing:
        new_js += f'  "{u}",\n'
    new_js += "];"

    p.write_text(new_js, encoding="utf-8")
    return True, len(existing)

# ========== DRIVER ==========
def build_driver():
    opts = Options()
    opts.add_argument("--headless=new")  # nếu lỗi: "--headless"
    opts.add_argument("--disable-gpu")
    opts.add_argument("--window-size=1280,720")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.page_load_strategy = "none"

    prefs = {
        "profile.managed_default_content_settings.images": 2,
        "profile.managed_default_content_settings.fonts": 2,
        "profile.managed_default_content_settings.notifications": 2,
    }
    opts.add_experimental_option("prefs", prefs)

    # performance logs
    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=opts)

def hard_reset_before_each(driver):
    try:
        driver.delete_all_cookies()
    except WebDriverException:
        pass
    driver.get(DOWNR)

def ensure_downr_ready(driver, wait):
    # Always ensure we're on DOWNR
    if "downr.org" not in (driver.current_url or ""):
        driver.get(DOWNR)

    # Prefer visible element (not just present)
    try:
        return wait.until(EC.visibility_of_element_located((By.XPATH, INPUT_XPATH)))
    except TimeoutException:
        driver.get(DOWNR)
        try:
            return wait.until(EC.visibility_of_element_located((By.XPATH, INPUT_XPATH)))
        except TimeoutException:
            return wait.until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='url'], input[type='text'], input"))
            )

def robust_clear_and_type(el, text):
    el.click()
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.BACKSPACE)
    el.send_keys(text)

def ensure_download_button(wait):
    try:
        return wait.until(EC.element_to_be_clickable((By.XPATH, BTN_XPATH)))
    except TimeoutException:
        return wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))

# ========== NETWORK CAPTURE ==========
def iter_perf_messages(driver):
    for entry in driver.get_log("performance"):
        try:
            yield json.loads(entry["message"])["message"]
        except Exception:
            continue

def try_get_body_json(driver, request_id, max_retry=24, retry_sleep=0.12):
    for _ in range(max_retry):
        try:
            body_obj = driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
            body = body_obj.get("body", "")
            if not body:
                time.sleep(retry_sleep)
                continue
            return json.loads(body)
        except Exception:
            time.sleep(retry_sleep)
    return None

def wait_nyt_json(driver, timeout_sec=18):
    deadline = time.time() + timeout_sec
    last_request_id = None

    while time.time() < deadline:
        for msg in iter_perf_messages(driver):
            if msg.get("method") != "Network.responseReceived":
                continue
            params = msg.get("params", {}) or {}
            resp = params.get("response", {}) or {}
            url = resp.get("url", "") or ""
            request_id = params.get("requestId")

            if request_id and TARGET_SUBSTR in url:
                last_request_id = request_id
                data = try_get_body_json(driver, request_id)
                if isinstance(data, dict):
                    return data
        time.sleep(0.08)

    if last_request_id:
        return try_get_body_json(driver, last_request_id, max_retry=36, retry_sleep=0.15)
    return None

# ========== PROGRESS / ETA ==========
@dataclass
class Stats:
    total: int
    done: int = 0
    ok: int = 0
    fail: int = 0
    dup: int = 0
    start_ts: float = 0.0
    last_update_ts: float = 0.0
    ema_sec_per_item: Optional[float] = None  # Exponential moving avg

def fmt_hms(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"

def render_bar(stats: Stats, width=28) -> str:
    pct = 0 if stats.total == 0 else stats.done / stats.total
    filled = int(round(pct * width))
    bar = "█" * filled + "░" * (width - filled)
    return bar

def update_ema(stats: Stats, item_sec: float, alpha=0.25):
    if stats.ema_sec_per_item is None:
        stats.ema_sec_per_item = item_sec
    else:
        stats.ema_sec_per_item = alpha * item_sec + (1 - alpha) * stats.ema_sec_per_item

def print_progress(stats: Stats, note: str = ""):
    now = time.time()
    elapsed = now - stats.start_ts
    rate = (stats.done / elapsed) if elapsed > 0 and stats.done > 0 else 0.0
    if stats.ema_sec_per_item:
        remaining = (stats.total - stats.done) * stats.ema_sec_per_item
    else:
        remaining = 0.0

    bar = render_bar(stats)
    pct = 0 if stats.total == 0 else (stats.done / stats.total) * 100.0

    line = (
        f"\r[{bar}] {pct:6.2f}%  {stats.done}/{stats.total}  "
        f"ok={stats.ok} fail={stats.fail} dup={stats.dup}  "
        f"rate={rate:.2f}/s  elapsed={fmt_hms(elapsed)}  ETA={fmt_hms(remaining)}"
    )
    if note:
        line += f"  | {note}"

    sys.stdout.write(line)
    sys.stdout.flush()

def newline():
    sys.stdout.write("\n")
    sys.stdout.flush()

# ========== SEQUENTIAL RUN ==========
def process_one(driver, wait, video_url: str, reset_each: bool = True, nyt_timeout=18) -> Tuple[bool, bool]:
    """
    Return: (success, added_to_raw)
    success = bắt được /nyt JSON
    added_to_raw = append raw_list.js thành công (không trùng)
    """
    if reset_each:
        hard_reset_before_each(driver)

    input_box = ensure_downr_ready(driver, wait)
    robust_clear_and_type(input_box, video_url)

    btn = ensure_download_button(wait)
    btn.click()

    data = wait_nyt_json(driver, timeout_sec=nyt_timeout)
    if not isinstance(data, dict):
        return False, False

    # (tuỳ chọn) in FINAL VIDEO HD/SD:
    url, q = pick_best_video_url(data)
    if url:
        # chỉ in 1 dòng ngắn để không “spam”
        print(f"\n🎯 {q}: {url[:80]}{'...' if len(url)>80 else ''}")

    added, _count = append_to_raw_list_js(url)
    return True, added

def run_sequential(urls: List[str], reset_each=True, nyt_timeout=18):
    stats = Stats(total=len(urls), start_ts=time.time(), last_update_ts=time.time())
    driver = build_driver()
    wait = WebDriverWait(driver, 12)

    try:
        driver.get(DOWNR)

        # initial progress
        print_progress(stats, note="starting")

        for u in urls:
            t0 = time.time()
            ok, added = process_one(driver, wait, u, reset_each=reset_each, nyt_timeout=nyt_timeout)
            dt = time.time() - t0

            stats.done += 1
            update_ema(stats, dt)

            if ok:
                stats.ok += 1
            else:
                stats.fail += 1

            if added:
                # added to RAW_LIST
                pass
            else:
                stats.dup += 1  # đã tồn tại hoặc không add được (thường là duplicate)

            print_progress(stats)

        newline()
        total_elapsed = time.time() - stats.start_ts
        print(f"✅ Done. Total elapsed: {fmt_hms(total_elapsed)} | ok={stats.ok} fail={stats.fail} dup={stats.dup}")
        if stats.ema_sec_per_item:
            print(f"📌 Avg (EMA) sec/item: {stats.ema_sec_per_item:.2f}s | Predicted for {stats.total} items: {fmt_hms(stats.total * stats.ema_sec_per_item)}")
        print(f"📄 RAW list saved to: {RAW_JS_FILE}")

    finally:
        driver.quit()

# ========== PARALLEL MODE (MULTIPROCESS) ==========
# Selenium chạy song song: mỗi process có driver riêng.
# Lưu ý: append raw_list.js từ nhiều process sẽ tranh chấp -> cần lock.
# Để đơn giản & chắc chắn, mình cho parallel mode CHỈ trả kết quả về parent,
# rồi parent mới append vào raw_list.js (single-writer).

import multiprocessing as mp

def worker_run(urls_chunk: List[str], reset_each: bool, nyt_timeout: int, queue: mp.Queue):
    driver = build_driver()
    wait = WebDriverWait(driver, 12)
    try:
        driver.get(DOWNR)
        for u in urls_chunk:
            t0 = time.time()
            # chạy nhưng không append raw_list.js tại worker
            if reset_each:
                hard_reset_before_each(driver)
            input_box = ensure_downr_ready(driver, wait)
            robust_clear_and_type(input_box, u)
            btn = ensure_download_button(wait)
            btn.click()
            data = wait_nyt_json(driver, timeout_sec=nyt_timeout)
            ok = isinstance(data, dict)
            dt = time.time() - t0
            queue.put((u, ok, dt))
    finally:
        driver.quit()

def chunkify(lst: List[str], n_chunks: int) -> List[List[str]]:
    n_chunks = max(1, int(n_chunks))
    chunks = [[] for _ in range(n_chunks)]
    for i, item in enumerate(lst):
        chunks[i % n_chunks].append(item)
    return [c for c in chunks if c]

def run_parallel(urls: List[str], workers: int = 2, reset_each=True, nyt_timeout=18):
    workers = max(1, int(workers))
    stats = Stats(total=len(urls), start_ts=time.time(), last_update_ts=time.time())

    q: mp.Queue = mp.Queue()
    chunks = chunkify(urls, workers)

    procs = []
    for ch in chunks:
        p = mp.Process(target=worker_run, args=(ch, reset_each, nyt_timeout, q), daemon=True)
        p.start()
        procs.append(p)

    # parent single-writer to raw_list.js
    print_progress(stats, note=f"parallel workers={workers}")

    finished = 0
    try:
        while finished < stats.total:
            u, ok, dt = q.get()  # blocks
            finished += 1
            stats.done += 1
            update_ema(stats, dt)

            if ok:
                stats.ok += 1
                added, _count = append_to_raw_list_js(u)
                if not added:
                    stats.dup += 1
            else:
                stats.fail += 1

            print_progress(stats)

        newline()
        total_elapsed = time.time() - stats.start_ts
        print(f"✅ Done (parallel). Total elapsed: {fmt_hms(total_elapsed)} | ok={stats.ok} fail={stats.fail} dup={stats.dup}")
        if stats.ema_sec_per_item:
            print(f"📌 Avg (EMA) sec/item: {stats.ema_sec_per_item:.2f}s | Predicted for {stats.total} items: {fmt_hms(stats.total * stats.ema_sec_per_item)}")
        print(f"📄 RAW list saved to: {RAW_JS_FILE}")

    finally:
        for p in procs:
            if p.is_alive():
                p.join(timeout=1.0)

# ========== ENTRY ==========
def main():
    urls = read_urls(INPUT_FILE)
    if not urls:
        print("❌ input.txt không có URL hợp lệ.")
        return

    # ---- Simple CLI flags (no extra deps) ----
    # Usage:
    #   python script.py
    #   python script.py --workers 3
    args = sys.argv[1:]
    workers = 1
    if "--workers" in args:
        idx = args.index("--workers")
        if idx + 1 < len(args):
            try:
                workers = int(args[idx + 1])
            except Exception:
                workers = 1

    if workers <= 1:
        run_sequential(urls, reset_each=True, nyt_timeout=18)
    else:
        run_parallel(urls, workers=workers, reset_each=True, nyt_timeout=18)

if __name__ == "__main__":
    main()