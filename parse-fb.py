import json
from urllib.parse import urlencode

INPUT = "graphql.har"
OUTPUT = "body.txt"

def get_post_text(entry):
    req = entry.get("request", {})
    pd = req.get("postData") or {}

    # Ưu tiên raw text
    text = pd.get("text")
    if isinstance(text, str) and text.strip():
        return text

    # Fallback: rebuild từ params
    params = pd.get("params")
    if isinstance(params, list) and params:
        kv = []
        for p in params:
            if "name" in p and "value" in p:
                kv.append((p["name"], p["value"]))
        return urlencode(kv, doseq=True)

    return None


with open(INPUT, "r", encoding="utf8") as f:
    har = json.load(f)

bodies = []

for e in har.get("log", {}).get("entries", []):
    req = e.get("request", {})
    if req.get("method") == "POST" and "/api/graphql" in (req.get("url") or ""):
        body = get_post_text(e)
        if body and body.startswith("av="):
            bodies.append(body)

with open(OUTPUT, "w", encoding="utf8") as f:
    f.write("\n\n".join(bodies))

print(f"✅ Saved {len(bodies)} graphql bodies to {OUTPUT}")