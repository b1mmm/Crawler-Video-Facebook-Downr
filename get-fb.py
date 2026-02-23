#COOKIE = "datr=sBwoabcFLS_qB3oMObYpK3R3; sb=txwoaSzWR8QP-I4vfOtU3Uit; ps_l=1; ps_n=1; locale=vi_VN; c_user=61566827097332; pas=61566827097332%3A6mdBYqXvNt; vpd=v1%3B464x73x2.0000000596046448; wl_cbv=v2%3Bclient_version%3A3096%3Btimestamp%3A1771820300; fbl_st=101524491%3BT%3A29530340; dpr=1.5; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1771820426929%2C%22v%22%3A1%7D; fr=2DbXCTupr6V6cUVqL.AWf99Llm72Xz8xfyGSq-B3O8tkxgK3T3-xc27i8qEqXFdn0hl3M.Bpm9bP..AAA.0.0.Bpm9bP.AWd2emhsxzhva40qdBkiOjFvchI; xs=50%3AD-vuf2vufIFkTw%3A2%3A1771815886%3A-1%3A-1%3A%3AAczH7F6sr2_drF2sW5iUpAi5VQked94TvUGiitLxog; wd=331x1298"


import requests
import json
import os

url = "https://www.facebook.com/api/graphql/"

headers = {
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

# DÁN COOKIE FACEBOOK CỦA BẠN
COOKIE = "datr=sBwoabcFLS_qB3oMObYpK3R3; sb=txwoaSzWR8QP-I4vfOtU3Uit; ps_l=1; ps_n=1; locale=vi_VN; c_user=61566827097332; pas=61566827097332%3A6mdBYqXvNt; vpd=v1%3B464x73x2.0000000596046448; wl_cbv=v2%3Bclient_version%3A3096%3Btimestamp%3A1771820300; fbl_st=101524491%3BT%3A29530340; dpr=1.5; presence=C%7B%22t3%22%3A%5B%5D%2C%22utc3%22%3A1771820426929%2C%22v%22%3A1%7D; fr=2DbXCTupr6V6cUVqL.AWf99Llm72Xz8xfyGSq-B3O8tkxgK3T3-xc27i8qEqXFdn0hl3M.Bpm9bP..AAA.0.0.Bpm9bP.AWd2emhsxzhva40qdBkiOjFvchI; xs=50%3AD-vuf2vufIFkTw%3A2%3A1771815886%3A-1%3A-1%3A%3AAczH7F6sr2_drF2sW5iUpAi5VQked94TvUGiitLxog; wd=331x1298"
headers["cookie"] = COOKIE

# DÁN FULL BODY THẬT (giống code cũ bạn đang chạy OK)
body = """av=61566827097332&__aaid=0&__user=61566827097332&__a=1&__req=38&__hs=20507.HYP%3Acomet_pkg.2.1...0&dpr=3&__ccg=GOOD&__rev=1033866714&__s=25vvi6%3A0r9roc%3A0j9y5r&__hsi=7609910287091706925&__dyn=7xeUjGU5a5Q1ryaxG4Vp41twWwIxu13wFwhUKbgS3q2ibwNw9G2Saw8i2S1DwUx60GE3Qwb-q7oc81EEc87m221Fwgo9oO0n24oaEnxO0Bo7O2l2Utwqo5W1ywiE4u9x-3m1mzXw8W58jwGzEaE5e3ym2SU4i5oe8cEW4-5pUfEe88o4Wm7-2K1yw9q2-awLyESE7i3C22390bS16xi4UK2K2WEjxK2B08-269wqQ1FwgUjz89oeE-5oabDzUiBG2OUqwjVqwLwcO11wo83KwHwOyUqxG0K8&__csr=gpNkt2IbNIjsp6gHktd5s8PFMD5j8yddtsD8ymHkz4R6nkiijXh6AKxtWrsL4iNmiFlKB9HDJ4XmBqHuRaiCTri88QiSVKX98yXiiHC-GKiFlKvK98im4EyJ2XHSijWHAKh7GHCGm5lGeDDCAhpbCgHKF9GXKHVqgixbLDF5gKiEyF4uqaxquAiQaymq8CyUkhoS2aiSmuaAzpUa9awzF95yU9ofK48iAwLAx22-4oyEOQqmKA264axqdwl8myWxyimfyERe2eufVQibgyEixi8wGhEC17x-2iq3e2C6o4q8x27EiDgG58565E8VUW8wwzUlG3m4Egy8tw8WfxqczEc8e8d8gx22m68aEuxC2m1Aw2no3cCK0DVK3N0nU5O0LVdABgB2ogw59wgUOqi227A2fl0wwcZu2W3m14yodFHdwhU8odQ2auewAw-w0oc80xW068opwQwXg016SU0K6U1UofoxQ0b3wMg0TtwlS0oa1ew1IDgfUHg0qiw15y028a3e0iGayAdw37U1RA0aAc01zJg2UyE2dw9G0fqo08w82Qwzw56aaw3a80qIg15p82oo&__hsdp=gkj8i7ElgiAIkCGaggNh298qh9EoCzyyhWJEmggz8y2193GwQgx4G1miAp8W22ExyQAB329iasgOQhpAOF9rf6MCgAfmyxkGkdA1ib5YdMX3f5h1tBcbEMhOuu-8xl5aResJAqEzIyi_IBVq8raG27GpBAmvBdgyiQh59q4czyZ1YXaBBE8KnCy4VUKjW4Lq1hMlpQ6aiLEn8yGAmIR8UFLigkP2R5YAODAhmuutKhetuGKUgu4sFVk5IHgDG7uclebCQl5Kgk4B45L2Etz9OBVRCUNadhvDaiUPxm4Akyc98m9l6QGaikiDiA8fhkmA9gEFQut8xSt4yQSt2TBCkNeekBh1CGgeaxO4pUSmaK5C59m9yNpGGh4ByoGmAijoIkER1UN8DGiq78B17yQee4oHxOGCgMMfE-q9zoSufABKdKmu1ahFF6GsDikMxd0JiwxzEHe1qK5Ugwl98sDwk4u8U-299f2aOP0Gype4UO2617U2-whqwvUnw_w4XxG11cdG0l5O0ca2i1IwBwxwaLAwkVU2sx10NwlEuxC3C3GU5O4Hh898G2GE30w4Ax-0Lohwd20Bo2BwrU3Rxu1rw4Pw43wcy0PE0we14w7kw4vw4VwgU0gZwce682Gw9-0O81eEvwNwFw27E2Ow2JE3nwpUjwmE1Zo0Lq0um0si0iS0iC1Qw_wUw2uU&__hblp=1Cu8g6mq3i1Ywio29w8ii19Axe11m1uwfS48mwcC9xC0z87y2Gq2C8w8u0Wo4-dwgpElwOzUiwyDxa11wm85CEpwyglw8219wKwSwMwNwqE3-g6G0VV87m0FE4C19wkU6G3GaG2S1hzEy3-E5K0kup0wzU6i0EEuwce2i0yoy262u0TE2owSxy1mxW6o1k8jw4Aw2rrw961lwb-E3OwsU4e1ewRwSwPweqEeo7O2K0PE3Bwd65EK1IgS0gK1AwhpVU17U4S0VF8gw1721KUkAwUxy0GE2oCwhE21w4Wx-362C3q0pm1hwba0r20gm1mxC5opyEiUmwiEsxe1TwSw6xK1Pw_w74w4Kwfe3O0B86S0Mo27wrUG2Gew4eyU7i2S4oe83swkE11Uaopw&__sjsp=gkj8i7ElgiAIkCGagV1h298qh9EoCz2OipiaSBhpjEOQwwigVgQgx4G1mietETipmsyiin4NynLVV6O94gxcGimkJPlsugArNRG6iFgSg58ImMT4gF2jWO8BkFoAwSz1cCdUvC8j9gwyBpQ8VLXRu6UlyubyoW9AJ4hi98gO0hEoxadxG3J0lohc0z89ovg6-0CUdUlwHg8OwJxAwh8fl24kwJ2BgB1p0HgZ4gx3o5V3QU5O3O0DQ2l0Eyp8a8uyQ361Zwei1pg4q0eqw2wU0jEwto2eK0DEG2S039214w&__comet_req=15&fb_dtsg=NAfsOQ2bPH7dn-hj-HRktigs8qrEqjHJMTma95lddxHqTgJfzjPJh0w%3A50%3A1771815886&jazoest=25657&lsd=_USiQpTDqJ2t3t3FeaRfNI&__spin_r=1033866714&__spin_b=trunk&__spin_t=1771820310&__crn=comet.fbweb.CometGroupVideosRoute&fb_api_caller_class=RelayModern&fb_api_req_friendly_name=GroupsCometMediaVideosTabGridQuery&server_timestamps=true&variables=%7B%22count%22%3A8%2C%22cursor%22%3A%22AQHSZCp8Sz9qbBSnFQyc8J814HYG4sxQaZPKA9bxR1KyBPBk0Wp4yqtmNnTRGjBaI_sk9nTnQ3ZcSGStrsSNEzpaNQ%22%2C%22scale%22%3A3%2C%22id%22%3A%22697332711026460%22%7D&doc_id=9352040021563569"""

resp = requests.post(url, headers=headers, data=body, timeout=30)

print("STATUS:", resp.status_code)

text = resp.text or ""
if text.startswith("for (;;);"):
    text = text[8:]

# Nếu bị HTML/login thì in ra để biết ngay
if not text.strip().startswith("{"):
    print("NOT JSON (first 200 chars):", text[:200])
    raise SystemExit(1)

data = json.loads(text)

# ===== Extract node.url =====
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

print("FOUND URLS:", len(urls))

# ===== Write output.txt (append, no duplicates) =====
output_file = "output.txt"
existing = set()
if os.path.exists(output_file):
    with open(output_file, "r", encoding="utf-8") as f:
        existing = set(line.strip() for line in f if line.strip())

new_urls = [u for u in urls if u not in existing]

with open(output_file, "a", encoding="utf-8") as f:
    for u in new_urls:
        f.write(u + "\n")

print(f"Added {len(new_urls)} new urls -> {output_file}")