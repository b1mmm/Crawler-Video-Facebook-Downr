Facebook Group Video URL Extractor (Python)

====================================

Mục tiêu
--------

Script này dùng để:

- Gửi POST request tới Facebook GraphQL endpoint
- Chạy tuần tự nhiều body (lấy từ file body.txt)
- Parse response JSON Relay
- Extract tất cả node.url (video URLs)
- Tổng hợp URL không trùng
- Xuất ra file output.txt sau khi chạy xong toàn bộ danh sách body


Cấu trúc thư mục
----------------

project/
│
├── main.py        (script Python)
├── body.txt       (mỗi dòng là 1 GraphQL body)
├── output.txt     (kết quả video URLs)
└── readme.txt


Yêu cầu
-------

- Python 3.8+
- Thư viện requests

Cài đặt:

pip install requests


Chuẩn bị body.txt
-----------------

File body.txt:

- Mỗi dòng là 1 body POST dạng:

av=...&__user=...&fb_dtsg=...&variables=...&doc_id=...

Ví dụ:

av=123&__user=123&...&doc_id=9352040021563569
av=123&__user=123&...&doc_id=9352040021563569

Không xuống dòng giữa body.


Cấu hình cookie
---------------

Mở main.py và dán cookie Facebook tại biến:

COOKIE = "datr=...; sb=...; c_user=...; xs=...; fr=...; wd=331x1298;"


Cookie phải còn sống (đăng nhập hợp lệ).

Nếu cookie hết hạn → response sẽ không phải JSON.


Cách chạy
---------

python main.py


Kết quả
-------

Sau khi chạy xong:

- output.txt sẽ chứa toàn bộ video URL (mỗi dòng 1 link)
- URL được loại trùng
- File được ghi 1 lần sau khi xử lý hết body.txt


Workflow kỹ thuật
-----------------

body.txt
  ↓
POST https://www.facebook.com/api/graphql/
  ↓
Relay JSON response
  ↓
data.node.group_mediaset.media.edges[*].node.url
  ↓
deduplicate
  ↓
output.txt


Lưu ý quan trọng
----------------

- Đây là Facebook internal Relay GraphQL (không phải API public)
- Cookie + fb_dtsg + lsd phải match
- Session Facebook có thể hết hạn bất kỳ lúc nào
- Script không bypass bảo mật
- Chỉ dùng cho tài khoản của bạn


Gợi ý mở rộng
-------------

- Auto paginate bằng cursor
- Extract HD mp4 URL
- Telegram bot notify
- Batch download
- Cloudflare Worker pipeline

-------

GraphQL HAR Body Extractor
=========================

Utility script to extract raw POST bodies (application/x-www-form-urlencoded)
from Chrome DevTools HAR files, specifically targeting Facebook /api/graphql requests.

It outputs the original request body starting with:

av=....

without decoding or modifying any parameters.

Useful for:
- Reverse engineering GraphQL calls
- Replaying requests
- Automation / batching
- Worker or bot pipelines
- Debugging frontend network behavior


Files
-----

extract_graphql_body.py
    Main extractor script.

graphql.har
    Input HAR file exported from Chrome DevTools.

graphql_bodies.txt
    Output file containing raw POST bodies (one request per block).


Requirements
------------

Python 3.8+

No external libraries required.


How to Export HAR
-----------------

1. Open Chrome DevTools (F12)
2. Go to Network tab
3. Filter by: graphql
4. Enable "Preserve log"
5. Reload page
6. Right-click → Save all as HAR with content

Place the exported file as:

graphql.har


Usage
-----

Run:

python extract_graphql_body.py


Output:

graphql_bodies.txt

Each block contains a full raw POST body ready to replay.


Behavior
--------

- Reads graphql.har
- Finds POST requests to /api/graphql
- Extracts postData.text
- If text is missing, rebuilds body from postData.params
- Keeps original encoding (no decoding)
- Saves only entries starting with "av="


Example Output
--------------

av=61566827097332&__aaid=0&__user=...

(blank line)

av=61566827097332&__aaid=0&__user=...


Replay Example (Python)
----------------------

import requests

for body in open("graphql_bodies.txt"):
    requests.post(
        "https://www.facebook.com/api/graphql/",
        headers={"content-type":"application/x-www-form-urlencoded"},
        data=body
    )


Notes
-----

- This tool is for educational and debugging purposes.
- No authentication headers or cookies are included.
- HAR must be exported with content enabled.
- Some fields may be session-specific.


Author
------

Utility written for personal reverse engineering workflows.

Use responsibly.
