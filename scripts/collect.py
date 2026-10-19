"""Щоденний збір Signal Feed: RSS → відбір Claude → переказ українською → data/items.json."""
import json, os, re, datetime, urllib.request, html
import feedparser, trafilatura

SRC = json.load(open("scripts/sources.json"))
KEY = os.environ["ANTHROPIC_API_KEY"]
TODAY = datetime.date.today().isoformat()
MAX_ITEMS = int(os.environ.get("MAX_ITEMS", "25"))
RUBRICS = ["AI Signals","Model Watch","Policy Radar","Toolbox","Research Digest","PKM","Время и фокус","Письмо"]
UA = {"User-Agent": "Mozilla/5.0 SignalFeed/1.0"}

def feeds():
    for d in SRC["substack"]:
        yield f"https://{d}/feed"
    for t in SRC["medium_tags"]:
        yield f"https://medium.com/feed/tag/{t}"
    yield from SRC["ua"]
    yield from SRC.get("ru", [])
    for r in SRC["reddit"]:
        yield f"https://www.reddit.com/r/{r}/top/.rss?t=day"
    yield from SRC["extra"]

def claude(model, prompt, max_tokens):
    body = json.dumps({"model": model, "max_tokens": max_tokens,
                       "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request("https://api.anthropic.com/v1/messages", body,
        {"x-api-key": KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
    r = json.load(urllib.request.urlopen(req, timeout=300))
    txt = "".join(b.get("text", "") for b in r["content"])
    if not txt: print("empty:", r.get("stop_reason"), [b.get("type") for b in r["content"]])
    if not txt and r.get("stop_reason") == "max_tokens" and max_tokens < 32000:
        return claude(model, prompt, max_tokens * 4)  # модель израсходовала лимит на размышления — повтор с запасом
    return txt

items = json.load(open("data/items.json"))
seen = {i["url"] for i in items}
cutoff = datetime.datetime.utcnow() - datetime.timedelta(days=3)

cands = []
for f in feeds():
    try:
        d = feedparser.parse(f, request_headers=UA)
    except Exception as e:
        print("feed fail", f, e); continue
    for e in d.entries[:40]:
        url = e.get("link", "").split("?")[0]
        t = e.get("published_parsed") or e.get("updated_parsed")
        if not url or url in seen or (t and datetime.datetime(*t[:6]) < cutoff):
            continue
        summ = re.sub("<[^>]+>", " ", html.unescape(e.get("summary", "")))[:300]
        full = " ".join(x.get("value", "") for x in e.get("content", [])) or e.get("summary", "")
        full = re.sub(r"\s+", " ", re.sub("<[^>]+>", " ", html.unescape(full)))
        cands.append({"id": len(cands), "url": url, "title": e.get("title", ""), "src": d.feed.get("title", f), "summary": summ, "full": full})
print("candidates", len(cands))
if not cands: raise SystemExit

listing = "\n".join(f'{c["id"]}. [{c["src"]}] {c["title"]} — {c["summary"]}' for c in cands[:700])
pick = claude("claude-haiku-5-5", f"""Ти редактор Signal Feed. Теми: ШІ-автоматизації, агенти, моделі, PKM, тайм-менеджмент і фокус, принципи письма і постів, вплив ШІ на медіа/бізнес/суспільство.
Обери ВСІ справді глибокі матеріали (але не більше {MAX_ITEMS*2}) (аналіз, досвід, методика; НЕ новини-анонси, НЕ лістикли «10 інструментів», НЕ реклама, НЕ політика без зв'язку з технологіями).
Відповідь – лише JSON-масив id, найкращі першими.\n\n{listing}""", 4000)
print("pick:", pick[:500])
ids = [int(x) for x in re.findall(r"\d+", pick)]

added = 0
for i in ids:
    if added >= MAX_ITEMS or i >= len(cands): break
    c = cands[i]
    try:
        raw = trafilatura.fetch_url(c["url"]); text = trafilatura.extract(raw) if raw else None
    except Exception: text = None
    if (not text or len(text.split()) < 600) and len(c["full"].split()) > len((text or "").split()):
        text = c["full"]
    if not text or len(text.split()) < 600:
        try:
            req = urllib.request.Request("https://r.jina.ai/" + c["url"], headers=UA)
            j = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "ignore")
            if len(j.split()) > len((text or "").split()): text = j
        except Exception as ex: print("reader fail", ex)
    if not text or len(text.split()) < 700:
        print("skip thin", c["url"]); continue
    words = len(text.split())
    out = claude("claude-sonnet-5-5", f"""Сделай ГЛУБОКИЙ ПЕРЕСКАЗ (не перевод) статьи НА РУССКОМ ЯЗЫКЕ для публичного сайта Signal Feed. Читатель – аналитик и медиаменеджер, ему нужны аргументы, механизмы, цифры и примеры из статьи, а не общие слова.
Верни только JSON-объект:
{{"rubric": одна из {RUBRICS}, "author": "...", "title": "собственный информативный заголовок",
"thesis": "1–2 предложения – главная мысль",
"key": [5-6 пунктов «главное»: конкретные утверждения, цифры, выводы автора],
"body": [6-9 абзацев: логика аргумента автора по шагам, ключевые примеры и данные, контраргументы или ограничения, всего не больше {int(words*0.45)} слов, своими словами, без выдуманных фактов],
"why": [2-3 пункта «почему это важно» для медиа, бизнеса или личной продуктивности – твой анализ, помеченный как вывод],
"apply": [2-4 конкретных шага «что применить» читателю завтра],
"quote": "одна цитата до 15 слов на русском или пусто"}}
Естественный русский, короткое тире «–». Если статья пустая, рекламная или неглубокая – верни {{"skip": true}}.

Источник: {c["src"]}\nURL: {c["url"]}\nЗаголовок: {c["title"]}\n\n{text[:60000]}""", 10000)
    try:
        o = json.loads(out[out.find("{"):out.rfind("}")+1])
    except Exception:
        print("bad json", c["url"]); continue
    if o.get("skip"): print("skip by model", c["url"]); continue
    for model in ("claude-haiku-5-5", "claude-sonnet-5-5"):
      try:
        ukr = claude(model, "Переклади на природну українську мову значення полів title, thesis, key, body, why, apply, quote цього JSON. "
                     "Поверни лише JSON-об'єкт з тими самими ключами, коротке тире «–».\n\n" +
                     json.dumps({k: o.get(k) for k in ["title","thesis","key","body","why","apply","quote"]}, ensure_ascii=False), 10000)
        o["uk"] = json.loads(ukr[ukr.find("{"):ukr.rfind("}")+1]); break
      except Exception as ex:
        print("uk fail", model, ex)
    o.update({"date": TODAY, "source": c["src"], "url": c["url"], "minutes": max(1, round(words/220))})
    items.append(o); seen.add(c["url"]); added += 1; print("added", o["title"])

json.dump(items, open("data/items.json", "w"), ensure_ascii=False, indent=1)
print("added total", added)
