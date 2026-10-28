"""Массовый сбор URL фотографий отелей из базы в колонку hotels.photo_url.

Почему не Google/Bing, как в hotel_photos.py: при массовых автоматических запросах
оба отдают капчу либо «трендовую» ленту вместо результатов, и обходить бот-проверки
мы не стали. Вместо скрейпинга используется официальное API Википедии и
Wikimedia Commons: без браузера, без ключей, хотлинк с upload.wikimedia.org разрешён.
Фотографии находятся только для известных отелей — у остальных photo_url остаётся
NULL, и сайт показывает заглушку «Фото не найдено».

Оптимизации относительно пооотельного запуска hotel_photos.py:
  * вообще нет браузера — два HTTP-запроса к API на отель максимум;
  * результат пишется в БД сразу, прогон можно прервать и продолжить
    (обрабатываются только отели с photo_url IS NULL);
  * один URL не назначается двум отелям (поиск любит отдавать одну и ту же
    статью на похожие названия).

Запуск:
    python batch_photos.py                 # все отели без photo_url
    python batch_photos.py --max-hotels 20 # проба
    python batch_photos.py --ids 85761 225031

Переменная окружения DATABASE_URL, по умолчанию локальная otters_db.
hotel_photos.py (разовый поиск по одному отелю через браузер) остаётся как есть.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg

from hotel_photos import LOGGER, configure_logging

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://otters:hackathon@localhost:5432/otters_db"
)
USER_AGENT = "OttersHackathonPhotoBot/1.0 (https://github.com/ostrovok-hackathon-2026/otters)"
THUMB_WIDTH = 800
PAUSE_SECONDS = 0.4
# Слова, которые не считаются содержательной частью названия отеля.
STOPWORDS = {
    "отель", "отеля", "гостиница", "гостиницы", "хостел", "хостелы", "апарт",
    "апартаменты", "hotel", "hostel", "inn", "apart", "apartments", "house",
    "москва", "москве", "moscow", "на", "в", "и", "у", "the", "by",
}
BAD_PARENTHETICAL = re.compile(
    r"фильм|альбом|песня|группа|станция|улица|район|фамилия|значени", re.IGNORECASE
)
# Логотипы и карты — не фотографии отеля.
BAD_FILENAME = re.compile(r"logo|логотип|coat_of_arms|\bmap\b|wordmark", re.IGNORECASE)
# Статья должна состоять в «гостиничной» категории: отсекает тёзок
# (отель «Пётр I» — не статья о царе, «Садовническая» — не статья об улице).
HOTEL_CATEGORY = re.compile(r"гостиниц|хостел|hotel|отел", re.IGNORECASE)
# Для файлов Commons достаточно и «архитектурного» слова: Building, фасад, вид.
COMMONS_HINT = re.compile(r"гостиниц|хостел|hotel|отел|building|здание|фасад|facade|view|вид", re.IGNORECASE)

PENDING_SQL = """
    SELECT id, name FROM hotels
    WHERE photo_url IS NULL
      AND name IS NOT NULL AND btrim(name) <> '' AND lower(btrim(name)) <> 'unknown'
    ORDER BY stars DESC NULLS LAST, id
"""


def api_get(host: str, params: dict) -> dict:
    url = f"https://{host}/w/api.php?{urlencode({'format': 'json', 'action': 'query', **params})}"
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def name_tokens(value: str) -> list[str]:
    cleaned = unicodedata.normalize("NFKC", value).lower()
    cleaned = re.sub(r"[«»\"'()\[\],.–—-]+", " ", cleaned)
    return [t for t in cleaned.split() if len(t) >= 3 and t not in STOPWORDS]


def title_matches(title: str, tokens: list[str]) -> bool:
    """Заголовок должен содержать все содержательные слова названия, а уточнение
    в скобках — быть про отель или город, но не про фильм/улицу/станцию."""
    if not tokens:
        return False
    normalized = unicodedata.normalize("NFKC", title).lower()
    if not all(token in normalized for token in tokens):
        return False
    parenthetical = re.search(r"\(([^)]*)\)", title)
    return not (parenthetical and BAD_PARENTHETICAL.search(parenthetical.group(1)))


def _sorted_pages(data: dict) -> list[dict]:
    pages = (data.get("query") or {}).get("pages") or {}
    return sorted(pages.values(), key=lambda page: page.get("index", 99))


def search_wikipedia(name: str, tokens: list[str]) -> str | None:
    data = api_get("ru.wikipedia.org", {
        "generator": "search", "gsrsearch": f"{name} отель Москва", "gsrlimit": 5,
        "prop": "pageimages|categories", "piprop": "thumbnail", "pithumbsize": THUMB_WIDTH,
        "cllimit": "max",
    })

    def is_hotel_article(page: dict) -> bool:
        return any(
            HOTEL_CATEGORY.search(category.get("title", ""))
            for category in page.get("categories") or []
        )

    candidates = [
        page for page in _sorted_pages(data)
        if title_matches(page.get("title", ""), tokens) and page.get("thumbnail")
        and is_hotel_article(page)
        and not BAD_FILENAME.search(page["thumbnail"]["source"])
    ]
    # Среди подходящих статей московская важнее киевской или самарской тёзки.
    for page in candidates:
        if "москва" in page["title"].lower():
            return page["thumbnail"]["source"]
    return candidates[0]["thumbnail"]["source"] if candidates else None


def search_commons(name: str, tokens: list[str]) -> str | None:
    data = api_get("commons.wikimedia.org", {
        "generator": "search", "gsrsearch": f"{name} hotel Moscow",
        "gsrnamespace": 6, "gsrlimit": 5,
        "prop": "imageinfo", "iiprop": "url", "iiurlwidth": THUMB_WIDTH,
    })
    for page in _sorted_pages(data):
        if not title_matches(page.get("title", ""), tokens):
            continue
        info = (page.get("imageinfo") or [{}])[0]
        url = info.get("thumburl") or info.get("url")
        title = page.get("title", "")
        # Для Commons название файла должно само говорить, что это отель.
        if url and COMMONS_HINT.search(title) and not BAD_FILENAME.search(url) and not BAD_FILENAME.search(title):
            return url
    return None


def find_photo(name: str) -> str | None:
    tokens = name_tokens(name)
    if not tokens:
        return None
    for source in (search_wikipedia, search_commons):
        try:
            url = source(name, tokens)
        except Exception:
            LOGGER.exception("Сбой источника %s на отеле %r", source.__name__, name)
            url = None
        if url:
            return url
        time.sleep(PAUSE_SECONDS)
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-hotels", type=int, default=None)
    parser.add_argument("--ids", type=int, nargs="*", default=None)
    args = parser.parse_args(argv)

    configure_logging()
    connection = psycopg.connect(DATABASE_URL, autocommit=True)
    connection.execute("ALTER TABLE hotels ADD COLUMN IF NOT EXISTS photo_url TEXT")
    if args.ids:
        rows = connection.execute(
            "SELECT id, name FROM hotels WHERE id = ANY(%s)", (args.ids,)
        ).fetchall()
    else:
        rows = connection.execute(PENDING_SQL).fetchall()
    if args.max_hotels:
        rows = rows[: args.max_hotels]
    used_urls = {
        url for (url,) in connection.execute(
            "SELECT photo_url FROM hotels WHERE photo_url IS NOT NULL"
        ).fetchall()
    }
    print(f"К обработке: {len(rows)} отелей", flush=True)

    found = skipped = 0
    for index, (hotel_id, name) in enumerate(rows, 1):
        url = find_photo(name)
        if url and url in used_urls:
            url = None  # одна и та же картинка у двух отелей хуже, чем заглушка
        if url:
            connection.execute(
                "UPDATE hotels SET photo_url = %s WHERE id = %s AND photo_url IS NULL",
                (url, hotel_id),
            )
            used_urls.add(url)
            found += 1
            print(f"[{index}/{len(rows)}] ok  {name}", flush=True)
        else:
            skipped += 1
            if index % 25 == 0:
                print(f"[{index}/{len(rows)}] … найдено {found}", flush=True)
        time.sleep(PAUSE_SECONDS)

    connection.close()
    print(f"Готово: с фото {found}, без фото {skipped}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
