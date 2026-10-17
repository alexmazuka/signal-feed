"""Собирает статический сайт Signal Feed (RU + UK) из data/items.json.

Страницы: главная (свежие выпуски + темы), /issue/<дата>/, /a/<slug>/, /topic/<rubric>/, /archive/.
Украинская версия — те же страницы под /uk/. Плюс RSS, sitemap с hreflang, robots.txt, llms.txt, IndexNow-ключ.
Адрес сайта задаётся переменными SITE_URL и SITE_BASE (для своего домена: SITE_URL=https://feed.matsuka.online/ SITE_BASE=/).
"""
import json, os, re, html, datetime, shutil
from collections import defaultdict, OrderedDict

SITE = os.environ.get("SITE_URL") or "https://alexmazuka.github.io/signal-feed/"
BASE = os.environ.get("SITE_BASE") or "/signal-feed/"
SUBSCRIBE_ACTION = os.environ.get("SUBSCRIBE_ACTION") or ""  # адрес формы email-рассылки (Buttondown и т. п.)
GSC_VERIFY = os.environ.get("GSC_VERIFY") or ""              # код подтверждения Google Search Console
INDEXNOW_KEY = "5f1c9a7e3b2d4e8fa6c0d9b1e2f34a57"
TG = "https://t.me/signalfeedai"
YEAR = datetime.date.today().year

RUBRICS = ["AI Signals", "Model Watch", "Policy Radar", "Toolbox", "Research Digest", "PKM", "Время и фокус", "Письмо"]
RUB_SLUG = {"Время и фокус": "focus", "Письмо": "writing"}

L = {
 "ru": dict(
  prefix="", lang="ru", og="ru_RU", other="uk", other_label="UA",
  lede="Подборка важных сигналов об ИИ, технологиях и их влиянии на медиа, бизнес и общество.",
  kicker="Ежедневные выпуски · на русском", issues="Выпуски", topics="Темы", archive="Архив",
  fresh_issues="Свежие выпуски", all_archive="Архив →", topics_note="Пересказы из разных выпусков",
  fresh="Свежий выпуск", issue="Выпуск", texts="текстов", open_issue="Открыть выпуск →", all_n="Все {n} →",
  prev="← Предыдущий", next="Следующий →", min="мин", min_orig="мин оригинала", main="Главное",
  why="Почему это важно", apply="Что применить", source="Первоисточник", more="Ещё по теме", all="Все →",
  topic_n="Тема · {n} пересказов", arch_desc="Все выпуски Signal Feed", arch_n="{a} выпусков · {b} пересказов",
  sub_h="Получайте Signal Feed", sub_p="Каждое утро – новые глубокие тексты об ИИ, автоматизации, PKM и письме.",
  sub_tg="Telegram-канал", sub_email="Ваш email", sub_btn="Подписаться",
  rights="Пересказы идей со ссылкой на первоисточники. Права на оригиналы принадлежат авторам.",
  months=["января","февраля","марта","апреля","мая","июня","июля","августа","сентября","октября","ноября","декабря"],
  months_nom=["Январь","Февраль","Март","Апрель","Май","Июнь","Июль","Август","Сентябрь","Октябрь","Ноябрь","Декабрь"],
  rub={"AI Signals":"AI Signals","Model Watch":"Model Watch","Policy Radar":"Policy Radar","Toolbox":"Toolbox",
       "Research Digest":"Research Digest","PKM":"PKM","Время и фокус":"Время и фокус","Письмо":"Письмо"},
  note={"AI Signals":"Как ИИ меняет работу, бизнес и медиа","Model Watch":"Новые модели, релизы, открытые веса",
        "Policy Radar":"Регулирование, право, политика технологий","Toolbox":"Инструменты и рабочие приёмы",
        "Research Digest":"Исследования и данные","PKM":"Вторая память, заметки, системы знаний",
        "Время и фокус":"Тайм-менеджмент, внимание, ритм","Письмо":"Как писать тексты и посты"}),
 "uk": dict(
  prefix="uk/", lang="uk", og="uk_UA", other="ru", other_label="RU",
  lede="Добірка важливих сигналів про ШІ, технології та їхній вплив на медіа, бізнес і суспільство.",
  kicker="Щоденні випуски · українською", issues="Випуски", topics="Теми", archive="Архів",
  fresh_issues="Свіжі випуски", all_archive="Архів →", topics_note="Перекази з різних випусків",
  fresh="Свіжий випуск", issue="Випуск", texts="текстів", open_issue="Відкрити випуск →", all_n="Усі {n} →",
  prev="← Попередній", next="Наступний →", min="хв", min_orig="хв оригіналу", main="Головне",
  why="Чому це важливо", apply="Що застосувати", source="Першоджерело", more="Ще з теми", all="Усі →",
  topic_n="Тема · {n} переказів", arch_desc="Усі випуски Signal Feed", arch_n="{a} випусків · {b} переказів",
  sub_h="Отримуйте Signal Feed", sub_p="Щоранку – нові глибокі тексти про ШІ, автоматизацію, PKM і письмо.",
  sub_tg="Telegram-канал", sub_email="Ваш email", sub_btn="Підписатися",
  rights="Перекази ідей з посиланням на першоджерела. Права на оригінали належать авторам.",
  months=["січня","лютого","березня","квітня","травня","червня","липня","серпня","вересня","жовтня","листопада","грудня"],
  months_nom=["Січень","Лютий","Березень","Квітень","Травень","Червень","Липень","Серпень","Вересень","Жовтень","Листопад","Грудень"],
  rub={"AI Signals":"AI Signals","Model Watch":"Model Watch","Policy Radar":"Policy Radar","Toolbox":"Toolbox",
       "Research Digest":"Research Digest","PKM":"PKM","Время и фокус":"Час і фокус","Письмо":"Письмо"},
  note={"AI Signals":"Як ШІ змінює роботу, бізнес і медіа","Model Watch":"Нові моделі, релізи, відкриті ваги",
        "Policy Radar":"Регулювання, право, політика технологій","Toolbox":"Інструменти й робочі прийоми",
        "Research Digest":"Дослідження і дані","PKM":"Друга пам'ять, нотатки, системи знань",
        "Время и фокус":"Тайм-менеджмент, увага, ритм","Письмо":"Як писати тексти і пости"}),
}
TEXT_FIELDS = ["title", "thesis", "key", "body", "quote", "why", "apply"]
TR = dict(zip("абвгґдеєжзиіїйклмнопрстуфхцчшщьюяыэёъ",
              ["a","b","v","h","g","d","e","ie","zh","z","y","i","i","i","k","l","m","n","o","p","r","s","t","u","f","kh","ts","ch","sh","shch","","iu","ia","y","e","e",""]))
e = html.escape


def slugify(s, n=60):
    s = "".join(TR.get(c, c) for c in s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    return s[:n].rstrip("-") or "item"


def rub_slug(r):
    return RUB_SLUG.get(r) or slugify(r)


def tx(it, lang):
    """Текстовые поля пересказа на нужном языке (украинские – из it['uk'], иначе русские)."""
    src = it.get("uk") if lang == "uk" and it.get("uk") else it
    return {k: src.get(k, it.get(k)) for k in TEXT_FIELDS}


def write(path, content):
    path = os.path.join("site_out", path)
    os.makedirs(os.path.dirname(path) or "site_out", exist_ok=True)
    open(path, "w").write(content)


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False).replace("</", "<\\/") + "</script>"


def build_lang(lang, items, issues, by_rub):
    t = L[lang]
    P = BASE + t["prefix"]
    OP = BASE + L[t["other"]]["prefix"]
    udate = lambda d: f'{datetime.date.fromisoformat(d).day} {t["months"][datetime.date.fromisoformat(d).month - 1]}'
    url_a = lambda it: f"{P}a/{it['slug']}/"
    url_i = lambda d: f"{P}issue/{d}/"
    url_t = lambda r: f"{P}topic/{rub_slug(r)}/"
    abs_ = lambda p: SITE.rstrip("/") + "/" + p[len(BASE):] if p.startswith(BASE) else p

    def page(rel, title, desc, body, ogtype="website", ld=None):
        here, there = P + rel, OP + rel
        head = (f'<!doctype html><html lang="{t["lang"]}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
                f'<title>{e(title)}</title><meta name="description" content="{e(desc)}">'
                f'<link rel="canonical" href="{abs_(here)}">'
                f'<link rel="alternate" hreflang="{t["lang"]}" href="{abs_(here)}"><link rel="alternate" hreflang="{L[t["other"]]["lang"]}" href="{abs_(there)}">'
                f'<link rel="alternate" hreflang="x-default" href="{abs_(BASE + rel)}">'
                f'<meta name="robots" content="index,follow,max-snippet:-1,max-image-preview:large">'
                f'<meta property="og:site_name" content="Signal Feed"><meta property="og:locale" content="{t["og"]}">'
                f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}">'
                f'<meta property="og:type" content="{ogtype}"><meta property="og:url" content="{abs_(here)}">'
                f'<meta name="twitter:card" content="summary"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(desc)}">'
                + (f'<meta name="google-site-verification" content="{e(GSC_VERIFY)}">' if GSC_VERIFY else "") +
                f'<meta name="author" content="matsuka.online"><link rel="alternate" type="application/rss+xml" title="Signal Feed" href="{P}feed.xml">'
                f'<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
                f'<link href="https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,400;0,600;0,700;1,400&family=IBM+Plex+Sans:wght@400;500&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">'
                f'<link rel="stylesheet" href="{BASE}style.css">' + (jsonld(ld) if ld else "") + '</head><body>'
                f'<header class="bar"><div class="wrap"><a class="logo" href="{P}">Signal Feed</a><nav class="nav">'
                f'<a href="{P}#issues">{t["issues"]}</a><a href="{P}#topics">{t["topics"]}</a><a href="{P}archive/">{t["archive"]}</a>'
                f'<a href="{TG}">Telegram</a><a class="lang" href="{there}" hreflang="{L[t["other"]]["lang"]}">{t["other_label"]}</a></nav></div></header>')
        foot = (f'<footer><div class="wrap"><span>© {YEAR} <a href="https://matsuka.online">matsuka.online</a> · Signal Feed · From feeds to insight</span>'
                f'<span>{t["rights"]} <a href="{P}feed.xml">RSS</a></span></div></footer></body></html>')
        write(t["prefix"] + rel + "index.html", head + body + foot)

    def card(it):
        x = tx(it, lang)
        return (f'<a class="card" href="{url_a(it)}"><span class="k">{e(t["rub"][it["rubric"]])} · {udate(it["date"])}</span>'
                f'<h3>{e(x["title"])}</h3><p>{e(x["thesis"])}</p><span class="k">{e(it["source"])} · {it.get("minutes", 5)} {t["min"]}</span></a>')

    sub_form = (f'<form action="{e(SUBSCRIBE_ACTION)}" method="post" target="_blank"><input type="email" name="email" required placeholder="{t["sub_email"]}" aria-label="{t["sub_email"]}">'
                f'<button type="submit">{t["sub_btn"]}</button></form>') if SUBSCRIBE_ACTION else ""
    subscribe = (f'<section class="sub" id="subscribe"><div><h2>{t["sub_h"]}</h2><p>{t["sub_p"]}</p></div>'
                 f'<div><div class="btns"><a class="btn solid" href="{TG}">{t["sub_tg"]} →</a><a class="btn" href="{P}feed.xml">RSS</a></div>{sub_form}</div></section>')

    # главная
    ic = []
    for n, (d, lst) in enumerate(list(issues.items())[:8]):
        rubs = " · ".join(OrderedDict.fromkeys(t["rub"][i["rubric"]] for i in lst))
        ic.append(f'<a class="issue-card{" first" if n == 0 else ""}" href="{url_i(d)}">'
                  f'<span class="k">{t["fresh"] if n == 0 else t["issue"]} · {len(lst)} {t["texts"]}</span>'
                  f'<div class="d">{udate(d)}</div><span class="k">{e(rubs)}</span>'
                  f'<ol>{"".join("<li>" + e(tx(i, lang)["title"]) + "</li>" for i in lst[:3])}</ol>'
                  f'<span class="more">{t["open_issue"]}</span></a>')
    topics = []
    for r in RUBRICS:
        lst = by_rub.get(r)
        if lst:
            topics.append(f'<div class="topic"><div class="th"><div><h3>{e(t["rub"][r])}</h3> <span>{e(t["note"][r])}</span></div>'
                          f'<a href="{url_t(r)}">{t["all_n"].format(n=len(lst))}</a></div><div class="rail">{"".join(card(i) for i in lst[:6])}</div></div>')
    home = (f'<div class="wrap"><section class="hero"><span class="k">{t["kicker"]}</span><h1>Signal Feed</h1>'
            f'<p>{t["lede"]}</p><p class="tag">From feeds to insight.</p></section>'
            f'<section class="sec" id="issues"><div class="sh"><h2>{t["fresh_issues"]}</h2><a href="{P}archive/">{t["all_archive"]}</a></div>'
            f'<div class="rail">{"".join(ic)}</div></section>'
            f'<section class="sec" id="topics"><div class="sh"><h2>{t["topics"]}</h2><span class="k">{t["topics_note"]}</span></div>{"".join(topics)}</section>'
            f'{subscribe}</div>')
    page("", "Signal Feed — From feeds to insight", t["lede"], home,
         ld={"@context": "https://schema.org", "@type": "WebSite", "name": "Signal Feed", "url": abs_(P), "inLanguage": t["lang"],
             "description": t["lede"], "publisher": {"@type": "Organization", "name": "matsuka.online", "url": "https://matsuka.online"}})

    # выпуски
    dates = list(issues)
    for idx, (d, lst) in enumerate(issues.items()):
        rows = "".join(
            f'<article class="row"><div class="n">{n:02d}</div><div><span class="k">{e(t["rub"][i["rubric"]])} · {e(i["source"])} · {i.get("minutes", 5)} {t["min"]}</span>'
            f'<h3><a href="{url_a(i)}">{e(tx(i, lang)["title"])}</a></h3><p>{e(tx(i, lang)["thesis"])}</p></div></article>'
            for n, i in enumerate(lst, 1))
        nav = [f'<a href="{url_i(dates[idx+1])}"><span class="k">{t["prev"]}</span>{t["issue"]} {udate(dates[idx+1])}</a>' if idx + 1 < len(dates) else "<span></span>"]
        if idx > 0:
            nav.append(f'<a href="{url_i(dates[idx-1])}" style="text-align:right"><span class="k">{t["next"]}</span>{t["issue"]} {udate(dates[idx-1])}</a>')
        body = (f'<div class="wrap"><div class="page-h"><span class="k">{t["issue"]} · {len(lst)} {t["texts"]}</span>'
                f'<h1>{udate(d)} {d[:4]}</h1><p>{e(" · ".join(OrderedDict.fromkeys(t["rub"][i["rubric"]] for i in lst)))}</p></div>'
                f'{rows}<div class="pn">{"".join(nav)}</div>{subscribe}</div>')
        page(f"issue/{d}/", f'{t["issue"]} {udate(d)} {d[:4]} — Signal Feed', "; ".join(tx(i, lang)["title"] for i in lst[:4]), body,
             ld={"@context": "https://schema.org", "@type": "ItemList", "name": f'{t["issue"]} {udate(d)}',
                 "itemListElement": [{"@type": "ListItem", "position": n, "url": abs_(url_a(i))} for n, i in enumerate(lst, 1)]})

    # пересказы
    for d, lst in issues.items():
        for it in lst:
            x = tx(it, lang)
            more = [m for m in by_rub[it["rubric"]] if m is not it][:3]
            lists = lambda title, arr: (f'<div class="sec2"><h2>{title}</h2><ul>{"".join("<li>" + e(a) + "</li>" for a in arr)}</ul></div>' if arr else "")
            body = (f'<div class="wrap"><article class="art"><span class="k"><a href="{url_t(it["rubric"])}">{e(t["rub"][it["rubric"]])}</a> · '
                    f'<a href="{url_i(d)}">{t["issue"]} {udate(d)}</a> · {it.get("minutes", 5)} {t["min_orig"]}</span>'
                    f'<h1>{e(x["title"])}</h1><p class="lead">{e(x["thesis"])}</p>'
                    f'<div class="key"><span class="k">{t["main"]}</span><ol>{"".join("<li>" + e(k) + "</li>" for k in (x["key"] or []))}</ol></div>'
                    f'<div class="body">{"".join("<p>" + e(p) + "</p>" for p in (x["body"] or []))}</div>'
                    + (f'<blockquote>{e(x["quote"])}</blockquote>' if x.get("quote") else "")
                    + lists(t["why"], x.get("why")) + lists(t["apply"], x.get("apply")) +
                    f'<p class="src">{t["source"]}: <a href="{e(it["url"])}" target="_blank" rel="noopener">{e(it.get("author", ""))} — {e(it["source"])}</a></p>'
                    + (f'<div class="sec"><div class="sh"><h2>{t["more"]}</h2><a href="{url_t(it["rubric"])}">{t["all"]}</a></div>'
                       f'<div class="rail">{"".join(card(m) for m in more)}</div></div>' if more else "")
                    + f'</article>{subscribe}</div>')
            ld = {"@context": "https://schema.org", "@type": "Article", "headline": x["title"][:110], "description": x["thesis"],
                  "datePublished": d, "dateModified": d, "inLanguage": t["lang"], "url": abs_(url_a(it)),
                  "mainEntityOfPage": abs_(url_a(it)), "articleSection": t["rub"][it["rubric"]],
                  "author": {"@type": "Organization", "name": "Signal Feed · matsuka.online", "url": "https://matsuka.online"},
                  "publisher": {"@type": "Organization", "name": "matsuka.online", "url": "https://matsuka.online"},
                  "isBasedOn": {"@type": "CreativeWork", "url": it["url"], "author": it.get("author", ""), "publisher": it["source"]},
                  "keywords": ", ".join([t["rub"][it["rubric"]], "ИИ" if lang == "ru" else "ШІ", "AI"])}
            page(f"a/{it['slug']}/", f'{x["title"]} — Signal Feed', x["thesis"], body, "article", ld)

    # темы
    for r in RUBRICS:
        lst = by_rub.get(r, [])
        if lst:
            body = (f'<div class="wrap"><div class="page-h"><span class="k">{t["topic_n"].format(n=len(lst))}</span><h1>{e(t["rub"][r])}</h1><p>{e(t["note"][r])}</p></div>'
                    f'<div class="sec"><div class="rail" style="grid-auto-flow:row;grid-template-columns:repeat(auto-fill,minmax(280px,1fr))">{"".join(card(i) for i in lst)}</div></div>{subscribe}</div>')
            page(f"topic/{rub_slug(r)}/", f'{t["rub"][r]} — Signal Feed', t["note"][r], body)

    # архив
    months = OrderedDict()
    for d, lst in issues.items():
        dd = datetime.date.fromisoformat(d)
        months.setdefault(f'{t["months_nom"][dd.month-1]} {dd.year}', []).append((d, lst))
    arch = "".join(f'<div class="mon">{m}</div><div class="list">' + "".join(
        f'<a href="{url_i(d)}"><b>{t["issue"]} {udate(d)}</b><span class="k">{len(lst)} {t["texts"]}</span></a>' for d, lst in v) + "</div>"
        for m, v in months.items())
    page("archive/", f'{t["archive"]} — Signal Feed', t["arch_desc"],
         f'<div class="wrap"><div class="page-h"><span class="k">{t["arch_n"].format(a=len(issues), b=len(items))}</span><h1>{t["archive"]}</h1></div>{arch}</div>')

    # RSS
    latest = sorted(items, key=lambda i: i["date"], reverse=True)[:50]
    rss = "".join(f"<item><title>{e(tx(i, lang)['title'])}</title><link>{abs_(url_a(i))}</link><guid>{abs_(url_a(i))}</guid>"
                  f"<pubDate>{datetime.date.fromisoformat(i['date']).strftime('%a, %d %b %Y 05:00:00 +0000')}</pubDate>"
                  f"<category>{e(t['rub'][i['rubric']])}</category><description>{e(tx(i, lang)['thesis'])}</description></item>" for i in latest)
    write(t["prefix"] + "feed.xml", f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Signal Feed</title><link>{abs_(P)}</link>'
          f'<description>{e(t["lede"])}</description><language>{t["lang"]}</language><copyright>© {YEAR} matsuka.online</copyright>{rss}</channel></rss>')


def main():
    items = json.load(open("data/items.json"))
    used = set()
    for it in items:
        s = it.get("slug") or slugify(it["title"])
        b, k = s, 2
        while s in used:
            s = f"{b}-{k}"; k += 1
        it["slug"] = s; used.add(s)
        if it.get("rubric") == "Час і фокус":
            it["rubric"] = "Время и фокус"
        if it.get("rubric") not in RUBRICS:
            it["rubric"] = "AI Signals"
    json.dump(items, open("data/items.json", "w"), ensure_ascii=False, indent=1)

    issues = OrderedDict()
    for it in sorted(items, key=lambda x: x["date"], reverse=True):
        issues.setdefault(it["date"], []).append(it)
    by_rub = defaultdict(list)
    for lst in issues.values():
        for it in lst:
            by_rub[it["rubric"]].append(it)

    if os.path.exists("site_out"):
        shutil.rmtree("site_out")
    os.makedirs("site_out")
    shutil.copy("scripts/style.css", "site_out/style.css")
    for lang in L:
        build_lang(lang, items, issues, by_rub)

    # sitemap с hreflang
    rels = ["", "archive/"] + [f"issue/{d}/" for d in issues] + [f"a/{i['slug']}/" for i in items] + [f"topic/{rub_slug(r)}/" for r in by_rub]
    last = {f"a/{i['slug']}/": i["date"] for i in items} | {f"issue/{d}/": d for d in issues}
    today = datetime.date.today().isoformat()
    urls = []
    for rel in rels:
        for lang in L:
            alt = "".join(f'<xhtml:link rel="alternate" hreflang="{L[l]["lang"]}" href="{SITE}{L[l]["prefix"]}{rel}"/>' for l in L)
            urls.append(f'<url><loc>{SITE}{L[lang]["prefix"]}{rel}</loc><lastmod>{last.get(rel, today)}</lastmod>{alt}</url>')
    write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
          'xmlns:xhtml="http://www.w3.org/1999/xhtml">' + "".join(urls) + "</urlset>")

    # robots: открыт для поисковиков и ИИ-ботов
    bots = ["Googlebot", "Google-Extended", "Bingbot", "GPTBot", "OAI-SearchBot", "ChatGPT-User", "ClaudeBot", "Claude-SearchBot",
            "Claude-User", "anthropic-ai", "PerplexityBot", "Perplexity-User", "Applebot", "Applebot-Extended", "CCBot", "YandexBot", "DuckDuckBot"]
    write("robots.txt", "".join(f"User-agent: {b}\nAllow: /\n\n" for b in bots) + f"User-agent: *\nAllow: /\n\nSitemap: {SITE}sitemap.xml\n")

    # llms.txt — карта сайта для ИИ-ассистентов
    lines = [f"# Signal Feed", "", f"> {L['ru']['lede']} From feeds to insight. © matsuka.online", "",
             "Ежедневные пересказы глубоких англоязычных текстов об ИИ, автоматизации, PKM, тайм-менеджменте и письме, "
             "на русском и украинском. Каждый пересказ ссылается на первоисточник.", "",
             f"- [Архив]({SITE}archive/)", f"- [Українська версія]({SITE}uk/)", f"- [RSS]({SITE}feed.xml)", "", "## Пересказы", ""]
    for it in sorted(items, key=lambda x: x["date"], reverse=True)[:300]:
        lines.append(f"- [{it['title']}]({SITE}a/{it['slug']}/): {it['thesis']}")
    write("llms.txt", "\n".join(lines) + "\n")

    write(f"{INDEXNOW_KEY}.txt", INDEXNOW_KEY)
    open("site_out/.nojekyll", "w").close()
    if SITE.startswith("https://") and "github.io" not in SITE:
        write("CNAME", SITE.split("//")[1].strip("/"))
    print("built", len(issues), "issues", len(items), "items")


if __name__ == "__main__":
    main()
