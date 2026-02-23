from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import json
import time
from pathlib import Path

DOWNR = "https://downr.org/"
TARGET_SUBSTR = "/.netlify/functions/nyt"

INPUT_FILE = "input.txt"
# OUTPUT_FILE = "results.jsonl"

INPUT_XPATH = "//input[@placeholder='Paste URL here']"
BTN_XPATH = "//button[normalize-space()='Download']"

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

    opts.set_capability("goog:loggingPrefs", {"performance": "ALL"})
    return webdriver.Chrome(options=opts)

def iter_perf_messages(driver):
    for entry in driver.get_log("performance"):
        try:
            yield json.loads(entry["message"])["message"]
        except Exception:
            continue

def try_get_body_json(driver, request_id, max_retry=20, retry_sleep=0.12):
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
        return try_get_body_json(driver, last_request_id, max_retry=30, retry_sleep=0.15)
    return None

RAW_JS_FILE = "raw_list.js"

def append_to_raw_list_js(url, path=RAW_JS_FILE):
    p = Path(path)

    # Nếu chưa tồn tại -> tạo skeleton
    if not p.exists():
        p.write_text("const RAW_LIST = [\n];", encoding="utf-8")

    text = p.read_text(encoding="utf-8")

    # extract list hiện tại
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("raw_list.js format invalid")

    body = text[start+1:end].strip()

    existing = []
    if body:
        for line in body.splitlines():
            line = line.strip().rstrip(",")
            if line.startswith('"') and line.endswith('"'):
                existing.append(line.strip('"'))

    # tránh trùng
    if url in existing:
        print("⚠️ URL đã tồn tại trong RAW_LIST, skip.")
        return existing

    existing.append(url)

    # rebuild file
    new_js = "const RAW_LIST = [\n"
    for u in existing:
        new_js += f'  "{u}",\n'
    new_js += "];"

    p.write_text(new_js, encoding="utf-8")

    return existing


def extract_safe_metadata(data, input_url):
    """
    Không dùng medias.
    Không parse JSON phức tạp.
    Chỉ append input_url vào RAW_LIST JS.
    """

    urls = append_to_raw_list_js(input_url)

    return {
        "input_url": input_url,
        "raw_count": len(urls) if urls else None,
        "added": True
    }

def read_urls(path: str):
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

def pick_best_video_url(resp_json):
    medias = resp_json.get("medias", []) or []

    # One-liner style (ưu tiên HD rồi fallback SD), có lọc type=video cho an toàn
    video = next(
        (m for m in medias if m.get("type") == "video" and m.get("quality") == "HD"),
        next((m for m in medias if m.get("type") == "video" and m.get("quality") == "SD"), None)
    )

    return (video.get("url"), video.get("quality")) if video else (None, None)
    
def ensure_downr_ready(driver, wait):
    """
    Đảm bảo Downr đang ở trạng thái có input để nhập URL.
    Fix lỗi lần 2 bị Timeout do UI đổi state / rerender.
    """
    # luôn quay về đúng trang
    if "downr.org" not in (driver.current_url or ""):
        driver.get(DOWNR)

    # 1) thử tìm input theo placeholder (visible)
    try:
        return wait.until(EC.visibility_of_element_located((By.XPATH, INPUT_XPATH)))
    except TimeoutException:
        pass

    # 2) reset state bằng load lại trang
    driver.get(DOWNR)
    try:
        return wait.until(EC.visibility_of_element_located((By.XPATH, INPUT_XPATH)))
    except TimeoutException:
        pass

    # 3) fallback rộng hơn (trường hợp placeholder đổi)
    return wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='url'], input[type='text'], input")))

def robust_clear_and_type(el, text):
    el.click()
    # clear chắc chắn (thay cho el.clear())
    el.send_keys(Keys.CONTROL, "a")
    el.send_keys(Keys.BACKSPACE)
    el.send_keys(text)

def main():
    urls = read_urls(INPUT_FILE)
    if not urls:
        print("❌ input.txt không có URL hợp lệ.")
        return

    driver = build_driver()
    wait = WebDriverWait(driver, 12)

    try:
        driver.get(DOWNR)

        for i, video_url in enumerate(urls, 1):
            print(f"\n[{i}/{len(urls)}] ▶ Xử lý: {video_url}")

            # ✅ luôn đảm bảo UI sẵn sàng trước mỗi URL
            input_box = ensure_downr_ready(driver, wait)
            robust_clear_and_type(input_box, video_url)

            # click download (có fallback nhẹ)
            try:
                btn = wait.until(EC.element_to_be_clickable((By.XPATH, BTN_XPATH)))
            except TimeoutException:
                btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button")))
            btn.click()

            # ✅ bắt nyt json (phải check trước khi dùng)
            data = wait_nyt_json(driver, timeout_sec=18)
            if not isinstance(data, dict):
                print("  ❌ Không lấy được response /nyt")
                time.sleep(0.2)
                continue

            # ✅ xử lý chọn video HD/SD (nếu bạn vẫn cần in link)
            url, q = pick_best_video_url(data)
            if url:
                print(f"🎯 FINAL VIDEO ({q}):")
                print(url)
            else:
                print("❌ Có JSON nhưng không tìm thấy medias video HD/SD.")
                print("Keys:", list(data.keys()))
                print("Medias len:", len(data.get("medias", []) or []))

            # ✅ nếu bạn vẫn muốn “trích metadata” kiểu mới
            # (ví dụ: append input_url vào raw_list.js)
            extract_safe_metadata(data, url)

            # (tuỳ chọn) nghỉ nhẹ để UI/network ổn định nếu chạy danh sách dài
            time.sleep(0.2)

    finally:
        driver.quit()

    print(f"\n✅ Done.")


if __name__ == "__main__":
    main()