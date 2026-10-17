"""Сообщает поисковикам (Bing, Yandex, Seznam, Naver через IndexNow) о новых страницах из последнего выпуска."""
import json, os, urllib.request, datetime
from build import SITE, INDEXNOW_KEY, L
items = json.load(open("data/items.json"))
last = max(i["date"] for i in items)
urls = [SITE, SITE + "uk/", SITE + "sitemap.xml"]
for i in items:
    if i["date"] == last:
        urls += [f"{SITE}{L[l]['prefix']}a/{i['slug']}/" for l in L] + [f"{SITE}{L[l]['prefix']}issue/{last}/" for l in L]
host = SITE.split("//")[1].split("/")[0]
body = json.dumps({"host": host, "key": INDEXNOW_KEY, "keyLocation": SITE + INDEXNOW_KEY + ".txt", "urlList": sorted(set(urls))}).encode()
req = urllib.request.Request("https://api.indexnow.org/indexnow", body, {"Content-Type": "application/json; charset=utf-8"})
try:
    print("indexnow", urllib.request.urlopen(req, timeout=30).status, len(urls))
except Exception as ex:
    print("indexnow fail", ex)
