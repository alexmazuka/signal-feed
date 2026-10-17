import json, os, urllib.request, urllib.parse, html
SITE = "https://alexmazuka.github.io/signal-feed/"
items = json.load(open("data/items.json"))
try: posted = set(json.load(open("data/posted.json")))
except FileNotFoundError: posted = set()
tok, ch = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHANNEL"].strip()
for i in items:
    if i["url"] in posted: continue
    e = html.escape
    key = "\n".join(f"– {e(k)}" for k in i.get("key", [])[:4])
    text = (f"<b>{e(i['rubric'])}</b> · {e(i['source'])}\n\n<b>{e(i['title'])}</b>\n\n{e(i['thesis'])}\n\n{key}\n\n"
            f"<a href=\"{SITE}\">Читати переказ</a> · <a href=\"{e(i['url'])}\">Оригінал</a>")
    data = urllib.parse.urlencode({"chat_id": ch, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()
    r = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data))
    print(r.get("ok"), i["title"][:60]); posted.add(i["url"])
json.dump(sorted(posted), open("data/posted.json", "w"), ensure_ascii=False, indent=1)
