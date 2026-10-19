import json, os, time, urllib.request, urllib.parse, urllib.error, html
SITE = os.environ.get("SITE_URL") or "https://alexmazuka.github.io/signal-feed/"
items = json.load(open("data/items.json"))
try: posted = set(json.load(open("data/posted.json")))
except FileNotFoundError: posted = set()
tok, ch = os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_CHANNEL"].strip()
for i in items:
    if i["url"] in posted: continue
    e = html.escape
    key = "\n".join(f"– {e(k)}" for k in i.get("key", [])[:4])
    text = (f"<b>{e(i['rubric'])}</b> · {e(i['source'])}\n\n<b>{e(i['title'])}</b>\n\n{e(i['thesis'])}\n\n{key}\n\n"
            f"<a href=\"{SITE}a/{i['slug']}/\">Читать пересказ</a> · <a href=\"{e(i['url'])}\">Оригинал</a>")
    data = urllib.parse.urlencode({"chat_id": ch, "text": text, "parse_mode": "HTML", "disable_web_page_preview": "true"}).encode()
    for attempt in range(6):
        try:
            r = json.load(urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data)); break
        except urllib.error.HTTPError as ex:
            if ex.code != 429 or attempt == 5: raise
            wait = json.loads(ex.read() or b"{}").get("parameters", {}).get("retry_after", 30)
            print("429, жду", wait); time.sleep(wait + 1)
    print(r.get("ok"), i["title"][:60]); posted.add(i["url"])
    json.dump(sorted(posted), open("data/posted.json", "w"), ensure_ascii=False, indent=1)  # сохраняем после каждого поста — без дублей при сбое
    time.sleep(3)  # лимит Telegram на сообщения в канал
json.dump(sorted(posted), open("data/posted.json", "w"), ensure_ascii=False, indent=1)
