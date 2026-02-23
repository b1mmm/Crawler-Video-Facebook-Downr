import requests
import json
import os
from typing import List, Set, Tuple

URL = "https://www.facebook.com/api/graphql/"

HEADERS = {
    "accept": "*/*",
    "accept-language": "vi-VN,vi;q=0.9,fr-FR;q=0.8,fr;q=0.7,en-US;q=0.6,en;q=0.5",
    "content-type": "application/x-www-form-urlencoded",
    "priority": "u=1, i",

    "sec-ch-prefers-color-scheme": "light",
    "sec-ch-ua": "\"Not:A-Brand\";v=\"99\", \"Google Chrome\";v=\"145\", \"Chromium\";v=\"145\"",
    "sec-ch-ua-full-version-list": "\"Not:A-Brand\";v=\"99.0.0.0\", \"Google Chrome\";v=\"145.0.7632.77\", \"Chromium\";v=\"145.0.7632.77\"",
    "sec-ch-ua-mobile": "?1",
    "sec-ch-ua-model": "\"Nexus 5\"",
    "sec-ch-ua-platform": "\"Android\"",
    "sec-ch-ua-platform-version": "\"6.0\"",

    "sec-fetch-dest": "empty",
    "sec-fetch-mode": "cors",
    "sec-fetch-site": "same-origin",

    "x-asbd-id": "359341",
    "x-fb-friendly-name": "GroupsCometMediaVideosTabGridQuery",
    "x-fb-lsd": "_USiQpTDqJ2t3t3FeaRfNI",

    "referer": "https://www.facebook.com/groups/697332711026460/media/videos",
    "user-agent": "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36",
}

# DÁN COOKIE FACEBOOK CỦA BẠN (giữ nguyên như bạn đang dùng chạy OK)
COOKIE = "datr=sBwoabcFLS_qB3oMObYpK3R3; sb=txwoaSzWR8QP-I4vfOtU3Uit; ps_l=1; ps_n=1; locale=vi_VN; c_user=61566827097332; pas=61566827097332%3A6mdBYqXvNt; vpd=v1%3B464x73x2.0000000596046448; wl_cbv=v2%3Bclient_version%3A3096%3Btimestamp%3A1771820300; fbl_st=101524491%3BT%3A29530340; dpr=1.5; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1771820426929%2C%22v%22%3A1%7D; fr=2DbXCTupr6V6cUVqL.AWf99Llm72Xz8xfyGSq-B3O8tkxgK3T3-xc27i8qEqXFdn0hl3M.Bpm9bP..AAA.0.0.Bpm9bP.AWd2emhsxzhva40qdBkiOjFvchI; xs=50%3AD-vuf2vufIFkTw%3A2%3A1771815886%3A-1%3A-1%3A%3AAczH7F6sr2_drF2sW5iUpAi5VQked94TvUGiitLxog; wd=331x1298"
HEADERS["cookie"] = COOKIE

BODY_FILE = "body.txt"
OUTPUT_FILE = "output.txt"


def strip_fb_prefix(text: str) -> str:
    text = text.lstrip()
    if text.startswith("for (;;);"):
        text = text[len("for (;;);"):].lstrip()
    return text


def extract_urls_from_graphql_json(data: dict) -> List[str]:
    edges = (
        data.get("data", {})
            .get("node", {})
            .get("group_mediaset", {})
            .get("media", {})
            .get("edges", [])
    )
    urls = []
    for e in edges:
        u = e.get("node", {}).get("url")
        if u:
            urls.append(u)
    return urls


def load_bodies(path: str) -> List[str]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Không thấy file {path}")

    bodies = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            bodies.append(line)

    if not bodies:
        raise RuntimeError(f"{path} không có dòng body hợp lệ.")
    return bodies


def load_existing_urls(path: str) -> Set[str]:
    if not os.path.exists(path):
        return set()
    with open(path, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())


def main():
    bodies = load_bodies(BODY_FILE)
    print(f"Loaded {len(bodies)} bodies from {BODY_FILE}")

    # Nếu muốn nối thêm vào output.txt cũ thì giữ existing.
    # Nếu muốn output.txt chỉ là kết quả mới mỗi lần chạy, set existing=set()
    existing = load_existing_urls(OUTPUT_FILE)
    collected: Set[str] = set(existing)

    s = requests.Session()

    ok = 0
    fail = 0

    for idx, body in enumerate(bodies, start=1):
        try:
            resp = s.post(URL, headers=HEADERS, data=body, timeout=30)
            text = strip_fb_prefix(resp.text or "")

            if not text.startswith("{") and not text.startswith("["):
                fail += 1
                print(f"[{idx}/{len(bodies)}] NOT JSON | HTTP {resp.status_code} | snippet={text[:120]!r}")
                continue

            data = json.loads(text)

            # FB trả lỗi dạng JSON
            if isinstance(data, dict) and "error" in data:
                fail += 1
                print(f"[{idx}/{len(bodies)}] FB ERROR {data.get('error')} | {data.get('errorSummary')} | rid={data.get('rid')}")
                continue

            urls = extract_urls_from_graphql_json(data)
            for u in urls:
                collected.add(u)

            ok += 1
            print(f"[{idx}/{len(bodies)}] OK | HTTP {resp.status_code} | urls_found={len(urls)} | total_unique={len(collected)}")

        except Exception as e:
            fail += 1
            print(f"[{idx}/{len(bodies)}] EXCEPTION: {e}")

    # Ghi tổng hợp sau khi chạy xong hết body.txt
    # (ghi lại toàn bộ unique URLs)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for u in sorted(collected):
            f.write(u + "\n")

    print("\n=== DONE ===")
    print(f"OK: {ok} | FAIL: {fail}")
    print(f"Total unique URLs written to {OUTPUT_FILE}: {len(collected)}")


if __name__ == "__main__":
    main()