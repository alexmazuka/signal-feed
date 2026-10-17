"""Собирает статический сайт Signal Feed з data/items.json: головна, випуски, переказ, теми, архів, RSS, sitemap."""
import json, os, re, html, datetime, shutil
from collections import defaultdict, OrderedDict

BASE = "/signal-feed/"
SITE = "https://alexmazuka.github.io/signal-feed/"
RUBRICS = ["AI Signals", "Model Watch", "Policy Radar", "Toolbox", "Research Digest", "PKM", "Время и фокус", "Письмо"]
RUB_NOTE = {
    "AI Signals": "Как ИИ меняет работу, бизнес и медиа",
    "Model Watch": "Новые модели, релизы, открытые веса",
    "Policy Radar": "Регулирование, право, политика технологий",
    "Toolbox": "Инструменты и рабочие приёмы",
    "Research Digest": "Исследования и данные",
    "PKM": "Вторая память, заметки, системы знаний",
    "Время и фокус": "Тайм-менеджмент, внимание, ритм",
    "Письмо": "Как писать тексты и посты",
}
MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
MONTHS_NOM = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
TR = dict(zip("абвгґдеєжзиіїйклмнопрстуфхцчшщьюяыэёъ",
              ["a","b","v","h","g","d","e","ie","zh","z","y","i","i","i","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","iu","ia","y","e","e",""]))

e = html.escape


def slugify(s, n=60):
    s = "".join(TR.get(c, c) for c in s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].rstrip("-") or "item"


def udate(d):
    d = datetime.date.fromisoformat(d)
    return f"{d.day} {MONTHS[d.month - 1]}"


def rub_slug(r):
    return slugify(r)


CSS = """
:root{--bg:#fff;--ink:#0a0a0a;--mute:#6e6e6e;--line:#0a0a0a;--soft:#e8e8e8;--card:#f6f6f6;
--display:"Spectral",Georgia,serif;--body:"IBM Plex Sans",-apple-system,sans-serif;--mono:"IBM Plex Mono",ui-monospace,monospace}
@media (prefers-color-scheme:dark){:root{--bg:#0a0a0a;--ink:#f2f2f2;--mute:#8f8f8f;--line:#f2f2f2;--soft:#262626;--card:#141414}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:400 17px/1.6 var(--body)}
a{color:inherit;text-decoration:none}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px}
.bar{position:sticky;top:0;z-index:5;background:var(--bg);border-bottom:1px solid var(--soft)}
.bar .wrap{display:flex;align-items:center;justify-content:space-between;height:52px;gap:16px}
.logo{font:700 20px var(--display);letter-spacing:-.01em}
.nav{display:flex;gap:18px;font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.08em;overflow-x:auto;white-space:nowrap}
.nav a{color:var(--mute)}.nav a:hover,.nav a.on{color:var(--ink)}
.k{font:500 11px var(--mono);text-transform:uppercase;letter-spacing:.1em;color:var(--mute)}
.hero{padding:56px 0 40px;border-bottom:3px solid var(--line)}
.hero h1{font:700 clamp(52px,11vw,128px)/.9 var(--display);margin:0 0 18px;letter-spacing:-.03em}
.hero p{font:400 clamp(18px,2.4vw,23px)/1.4 var(--display);max-width:760px;margin:0}
.hero .tag{font-style:italic;color:var(--mute);margin-top:8px}
.sec{padding:44px 0 8px}
.sh{display:flex;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding-bottom:10px;margin-bottom:22px}
.sh h2{font:600 28px var(--display);margin:0}
.sh a{font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.08em}
.sh a:hover{text-decoration:underline}
.rail{display:grid;grid-auto-flow:column;grid-auto-columns:minmax(280px,1fr);gap:16px;overflow-x:auto;scroll-snap-type:x mandatory;padding-bottom:10px;scrollbar-width:thin}
.rail>*{scroll-snap-align:start}
.issue-card{display:flex;flex-direction:column;border:1px solid var(--line);padding:20px;min-height:300px;transition:background .15s,color .15s}
.issue-card:hover{background:var(--ink);color:var(--bg)}
.issue-card:hover .k{color:inherit;opacity:.7}
.issue-card .d{font:700 46px/1 var(--display);margin:10px 0 4px;letter-spacing:-.02em}
.issue-card ol{margin:16px 0 0;padding-left:18px;font:400 15px/1.4 var(--body)}
.issue-card ol li{margin-bottom:6px}
.issue-card .more{margin-top:auto;padding-top:14px;font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.08em}
.issue-card.first{background:var(--ink);color:var(--bg)}
.issue-card.first .k{color:inherit;opacity:.7}
.card{display:flex;flex-direction:column;background:var(--card);padding:20px;min-height:220px;border-top:3px solid var(--line);transition:transform .15s}
.card:hover{transform:translateY(-3px)}
.card h3{font:600 20px/1.25 var(--display);margin:10px 0 8px}
.card p{margin:0;font-size:15px;color:var(--mute);display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.card .k:last-child{margin-top:auto;padding-top:12px}
.topic{margin-bottom:34px}
.topic .th{display:flex;justify-content:space-between;align-items:baseline;margin-bottom:12px;gap:12px}
.topic .th h3{font:600 22px var(--display);margin:0}
.topic .th span{color:var(--mute);font-size:14px}
.topic .th a{font:500 12px var(--mono);text-transform:uppercase;letter-spacing:.08em;white-space:nowrap}
.page-h{padding:44px 0 22px;border-bottom:3px solid var(--line)}
.page-h h1{font:700 clamp(36px,6vw,64px)/1.05 var(--display);margin:8px 0 8px;letter-spacing:-.02em}
.page-h p{margin:0;color:var(--mute);font:400 19px var(--display)}
.row{display:grid;grid-template-columns:64px 1fr;gap:18px;padding:24px 0;border-bottom:1px solid var(--soft)}
.row .n{font:700 36px/1 var(--display)}
.row h3{font:600 24px/1.25 var(--display);margin:6px 0}
.row h3 a:hover{text-decoration:underline}
.row p{margin:0;max-width:70ch}
.art{max-width:720px;margin:0 auto;padding:44px 0}
.art h1{font:700 clamp(32px,5vw,52px)/1.1 var(--display);margin:10px 0 14px;letter-spacing:-.015em}
.art .lead{font:400 21px/1.45 var(--display);margin:0 0 26px}
.key{border:2px solid var(--line);padding:18px 22px;margin:0 0 30px}
.key ol{margin:8px 0 0;padding-left:20px}.key li{margin-bottom:6px}
.art .body p{font-size:18.5px;line-height:1.72;margin:0 0 18px}
blockquote{border-left:6px solid var(--line);margin:26px 0;padding:4px 0 4px 18px;font:italic 400 22px/1.4 var(--display)}
.src{border-top:1px solid var(--line);margin-top:30px;padding-top:16px;font:14px var(--mono)}
.src a{text-decoration:underline}
.pn{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin-top:30px}
.pn a{border:1px solid var(--soft);padding:14px;font:600 16px/1.3 var(--display)}
.pn a:hover{border-color:var(--line)}
.pn .k{display:block;margin-bottom:6px}
.mon{font:600 22px var(--display);margin:30px 0 8px}
.list a{display:flex;justify-content:space-between;gap:16px;padding:12px 0;border-bottom:1px solid var(--soft)}
.list a:hover b{text-decoration:underline}
.list b{font:600 18px/1.3 var(--display)}
footer{border-top:3px solid var(--line);margin-top:70px;padding:24px 0 48px}
footer .wrap{display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;font:12px var(--mono);color:var(--mute)}
footer a{text-decoration:underline}
@media (max-width:640px){.row{grid-template-columns:38px 1fr}.row .n{font-size:24px}.pn{grid-template-columns:1fr}.rail{grid-auto-columns:82%}.nav{gap:12px}}
"""

HEAD = """<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title><meta name="description" content="{desc}">
<meta property="og:title" content="{title}"><meta property="og:description" content="{desc}"><meta property="og:type" content="{ogtype}">
<link rel="alternate" type="application/rss+xml" title="Signal Feed" href="{base}feed.xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}style.css"></head><body>
<header class="bar"><div class="wrap"><a class="logo" href="{base}">Signal Feed</a>
<nav class="nav"><a href="{base}#issues">Выпуски</a><a href="{base}#topics">Темы</a><a href="{base}archive/">Архив</a><a href="https://t.me/signalfeedai">Telegram</a></nav></div></header>
"""
FOOT = """<footer><div class="wrap"><span>Signal Feed · From feeds to insight</span>
<span>Пересказы идей со ссылкой на первоисточники. Права на оригиналы принадлежат авторам. <a href="{base}feed.xml">RSS</a></span></div></footer></body></html>"""


def page(title, desc, body, ogtype="website"):
    return HEAD.format(title=e(title), desc=e(desc), base=BASE, ogtype=ogtype) + body + FOOT.format(base=BASE)


def write(path, content):
    path = os.path.join("site_out", path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    open(path, "w").write(content)


def main():
    items = json.load(open("data/items.json"))
    used = set()
    for it in items:
        s = it.get("slug") or slugify(it["title"])
        base, k = s, 2
        while s in used:
            s = f"{base}-{k}"; k += 1
        it["slug"] = s; used.add(s)
        if it.get("rubric") not in RUBRICS:
            it["rubric"] = "AI Signals"
    json.dump(items, open("data/items.json", "w"), ensure_ascii=False, indent=1)

    issues = OrderedDict()
    for it in sorted(items, key=lambda x: x["date"], reverse=True):
        issues.setdefault(it["date"], []).append(it)
    by_rub = defaultdict(list)
    for d, lst in issues.items():
        for it in lst:
            by_rub[it["rubric"]].append(it)

    if os.path.exists("site_out"):
        shutil.rmtree("site_out")
    os.makedirs("site_out")
    write("style.css", CSS)
    url_a = lambda it: f"{BASE}a/{it['slug']}/"
    url_i = lambda d: f"{BASE}issue/{d}/"
    url_t = lambda r: f"{BASE}topic/{rub_slug(r)}/"

    def card(it):
        return (f'<a class="card" href="{url_a(it)}"><span class="k">{e(it["rubric"])} · {udate(it["date"])}</span>'
                f'<h3>{e(it["title"])}</h3><p>{e(it["thesis"])}</p><span class="k">{e(it["source"])} · {it.get("minutes", 5)} мин</span></a>')

    # головна
    ic = []
    for n, (d, lst) in enumerate(list(issues.items())[:8]):
        dd = datetime.date.fromisoformat(d)
        rubs = " · ".join(OrderedDict.fromkeys(i["rubric"] for i in lst))
        ic.append(f'<a class="issue-card{" first" if n == 0 else ""}" href="{url_i(d)}">'
                  f'<span class="k">{"Свежий выпуск" if n == 0 else "Выпуск"} · {len(lst)} текстов</span>'
                  f'<div class="d">{dd.day} {MONTHS[dd.month-1]}</div><span class="k">{e(rubs)}</span>'
                  f'<ol>{"".join("<li>" + e(i["title"]) + "</li>" for i in lst[:3])}</ol>'
                  f'<span class="more">Открыть выпуск →</span></a>')
    topics = []
    for r in RUBRICS:
        lst = by_rub.get(r)
        if not lst:
            continue
        topics.append(f'<div class="topic"><div class="th"><div><h3>{e(r)}</h3> <span>{e(RUB_NOTE[r])}</span></div>'
                      f'<a href="{url_t(r)}">Все {len(lst)} →</a></div><div class="rail">{"".join(card(i) for i in lst[:6])}</div></div>')
    home = (f'<div class="wrap"><section class="hero"><span class="k">Ежедневные выпуски · на русском</span><h1>Signal Feed</h1>'
            f'<p>Подборка важных сигналов об ИИ, технологиях и их влиянии на медиа, бизнес и общество.</p>'
            f'<p class="tag">From feeds to insight.</p></section>'
            f'<section class="sec" id="issues"><div class="sh"><h2>Свежие выпуски</h2><a href="{BASE}archive/">Архив →</a></div>'
            f'<div class="rail">{"".join(ic)}</div></section>'
            f'<section class="sec" id="topics"><div class="sh"><h2>Темы</h2><span class="k">Пересказы из разных выпусков</span></div>{"".join(topics)}</section></div>')
    write("index.html", page("Signal Feed — From feeds to insight",
                             "Подборка важных сигналов об ИИ, технологиях и их влиянии на медиа, бизнес и общество.", home))

    # випуски
    dates = list(issues)
    for idx, (d, lst) in enumerate(issues.items()):
        rows = "".join(
            f'<article class="row"><div class="n">{n:02d}</div><div><span class="k">{e(i["rubric"])} · {e(i["source"])} · {i.get("minutes", 5)} мин</span>'
            f'<h3><a href="{url_a(i)}">{e(i["title"])}</a></h3><p>{e(i["thesis"])}</p></div></article>'
            for n, i in enumerate(lst, 1))
        nav = []
        if idx + 1 < len(dates): nav.append(f'<a href="{url_i(dates[idx+1])}"><span class="k">← Предыдущий</span>Выпуск {udate(dates[idx+1])}</a>')
        else: nav.append("<span></span>")
        if idx > 0: nav.append(f'<a href="{url_i(dates[idx-1])}" style="text-align:right"><span class="k">Следующий →</span>Выпуск {udate(dates[idx-1])}</a>')
        body = (f'<div class="wrap"><div class="page-h"><span class="k">Выпуск · {len(lst)} текстов</span>'
                f'<h1>{udate(d)} {d[:4]}</h1><p>{e(" · ".join(OrderedDict.fromkeys(i["rubric"] for i in lst)))}</p></div>'
                f'{rows}<div class="pn">{"".join(nav)}</div></div>')
        write(f"issue/{d}/index.html", page(f"Выпуск {udate(d)} — Signal Feed", lst[0]["thesis"], body))

    # перекази
    for d, lst in issues.items():
        for n, it in enumerate(lst):
            more = [x for x in by_rub[it["rubric"]] if x is not it][:3]
            body = (f'<div class="wrap"><article class="art"><span class="k"><a href="{url_t(it["rubric"])}">{e(it["rubric"])}</a> · '
                    f'<a href="{url_i(d)}">Выпуск {udate(d)}</a> · {it.get("minutes", 5)} мин оригинала</span>'
                    f'<h1>{e(it["title"])}</h1><p class="lead">{e(it["thesis"])}</p>'
                    f'<div class="key"><span class="k">Главное</span><ol>{"".join("<li>" + e(k) + "</li>" for k in it.get("key", []))}</ol></div>'
                    f'<div class="body">{"".join("<p>" + e(p) + "</p>" for p in it.get("body", []))}</div>'
                    + (f'<blockquote>{e(it["quote"])}</blockquote>' if it.get("quote") else "") +
                    f'<p class="src">Первоисточник: <a href="{e(it["url"])}" target="_blank" rel="noopener">{e(it.get("author", ""))} — {e(it["source"])}</a></p>'
                    + (f'<div class="sec"><div class="sh"><h2>Ещё по теме</h2><a href="{url_t(it["rubric"])}">Все →</a></div>'
                       f'<div class="rail">{"".join(card(x) for x in more)}</div></div>' if more else "")
                    + '</article></div>')
            write(f"a/{it['slug']}/index.html", page(f'{it["title"]} — Signal Feed', it["thesis"], body, "article"))

    # теми
    for r in RUBRICS:
        lst = by_rub.get(r, [])
        if not lst: continue
        body = (f'<div class="wrap"><div class="page-h"><span class="k">Тема · {len(lst)} пересказов</span><h1>{e(r)}</h1><p>{e(RUB_NOTE[r])}</p></div>'
                f'<div class="sec"><div class="rail" style="grid-auto-flow:row;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))">{"".join(card(i) for i in lst)}</div></div></div>')
        write(f"topic/{rub_slug(r)}/index.html", page(f"{r} — Signal Feed", RUB_NOTE[r], body))

    # архів
    months = OrderedDict()
    for d, lst in issues.items():
        dd = datetime.date.fromisoformat(d)
        months.setdefault(f"{MONTHS_NOM[dd.month-1]} {dd.year}", []).append((d, lst))
    arch = "".join(f'<div class="mon">{m}</div><div class="list">' + "".join(
        f'<a href="{url_i(d)}"><b>Выпуск {udate(d)}</b><span class="k">{len(lst)} текстов</span></a>' for d, lst in v) + "</div>"
        for m, v in months.items())
    write("archive/index.html", page("Архив — Signal Feed", "Все выпуски Signal Feed",
          f'<div class="wrap"><div class="page-h"><span class="k">{len(issues)} выпусков · {len(items)} пересказов</span><h1>Архив</h1></div>{arch}</div>'))

    # RSS + sitemap
    latest = sorted(items, key=lambda x: x["date"], reverse=True)[:50]
    rss = "".join(f"<item><title>{e(i['title'])}</title><link>{SITE}a/{i['slug']}/</link><guid>{SITE}a/{i['slug']}/</guid>"
                  f"<pubDate>{datetime.date.fromisoformat(i['date']).strftime('%a, %d %b %Y 05:00:00 +0000')}</pubDate>"
                  f"<category>{e(i['rubric'])}</category><description>{e(i['thesis'])}</description></item>" for i in latest)
    write("feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Signal Feed</title><link>{SITE}</link>'
          f'<description>From feeds to insight</description><language>ru</language>{rss}</channel></rss>')
    urls = [SITE, SITE + "archive/"] + [f"{SITE}issue/{d}/" for d in issues] + [f"{SITE}a/{i['slug']}/" for i in items] + \
           [f"{SITE}topic/{rub_slug(r)}/" for r in by_rub]
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
          + "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {SITE}sitemap.xml\n")
    open("site_out/.nojekyll", "w").close()
    print("built", len(issues), "issues", len(items), "items")


if __name__ == "__main__":
    main()
