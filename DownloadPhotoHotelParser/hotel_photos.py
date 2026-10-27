"""Поиск фотографий отелей в Google Images с резервом Bing Images.

Python 3.11+. Установка: pip install -r requirements.txt
Браузер: python -m playwright install chromium
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import logging
import re
import sys
from dataclasses import asdict, dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlparse
from urllib.request import Request, urlopen


BASE_DIR = Path(__file__).resolve().parent
LOG_FILE = BASE_DIR / "hotel_photos.log"
LOGGER = logging.getLogger("hotel_photos")
MAX_IMAGE_BYTES = 15 * 1024 * 1024
IMAGE_MIME_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/avif": ".avif",
    "image/bmp": ".bmp",
}


class PhotoParserError(Exception):
    """Базовая ошибка приложения."""


class SearchError(PhotoParserError):
    """Ошибка поиска изображений."""


class DownloadError(PhotoParserError):
    """Ошибка скачивания изображения."""


@dataclass(frozen=True, slots=True)
class Photo:
    """Ссылка на фотографию и данные о её происхождении."""

    url: str
    source: str
    title: str = ""
    page_url: str | None = None
    is_thumbnail: bool = False
    saved_as: str | None = None


class PhotoProvider(Protocol):
    """Контракт поискового источника (Dependency Inversion)."""

    name: str

    def search(self, page: Any, query: str, limit: int) -> list[Photo]:
        """Возвращает ссылки на картинки по запросу."""


def configure_logging() -> None:
    """Настраивает запись логов рядом с текущим скриптом."""
    LOGGER.setLevel(logging.INFO)
    LOGGER.propagate = False
    if LOGGER.handlers:
        return

    handler = RotatingFileHandler(
        LOG_FILE,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
        )
    )
    LOGGER.addHandler(handler)


def is_public_image_url(value: object) -> bool:
    """Проверяет формат URL и исключает явно локальные IP-адреса."""
    if not isinstance(value, str) or len(value) > 4096:
        return False

    try:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        if parsed.username or parsed.password:
            return False
        if parsed.hostname.lower() in {"localhost", "localhost.localdomain"}:
            return False
        try:
            address = ipaddress.ip_address(parsed.hostname)
        except ValueError:
            return True  # Доменное имя, не IP-литерал.
        return address.is_global
    except ValueError:
        return False


def normalize_hotel_name(value: str) -> str:
    """Проверяет поисковую строку без изменения написания названия."""
    cleaned = " ".join(value.split())
    if not cleaned or len(cleaned) > 200:
        raise ValueError("Название отеля должно содержать от 1 до 200 символов")
    return cleaned


def safe_directory_name(value: str) -> str:
    """Создаёт безопасное имя папки на основе названия отеля."""
    result = re.sub(r"[^\w\-. ]+", "_", value, flags=re.UNICODE)
    result = result.strip(" ._")[:80]
    return result or "hotel"


def parse_google_images(items: list[dict[str, Any]]) -> list[Photo]:
    """Превращает DOM-данные Google Images в объекты Photo."""
    photos: list[Photo] = []
    for item in items:
        url = item.get("src") or item.get("data_src")
        link = item.get("href") or ""
        if isinstance(link, str):
            parameters = parse_qs(urlparse(link).query)
            original = parameters.get("imgurl", [None])[0]
            if is_public_image_url(original):
                url = original

        if not is_public_image_url(url):
            continue
        if (item.get("width") or 0) < 90 or (item.get("height") or 0) < 65:
            continue

        hostname = urlparse(url).hostname or ""
        if hostname.endswith("google.com") or hostname.endswith("google.de"):
            continue

        reference = None
        if isinstance(link, str):
            parameters = parse_qs(urlparse(link).query)
            candidate = parameters.get("imgrefurl", [None])[0]
            if is_public_image_url(candidate):
                reference = candidate
            elif is_public_image_url(link) and "google." not in (
                urlparse(link).hostname or ""
            ):
                reference = link

        photos.append(
            Photo(
                url=url,
                source="google",
                title=str(item.get("alt") or ""),
                page_url=reference,
                is_thumbnail="gstatic.com" in hostname,
            )
        )
    return unique_photos(photos)


def parse_bing_images(items: list[str]) -> list[Photo]:
    """Разбирает JSON из атрибута m у карточек Bing Images."""
    photos: list[Photo] = []
    for raw in items:
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError):
            continue
        if not isinstance(payload, dict):
            continue

        url = payload.get("murl") or payload.get("turl")
        if not is_public_image_url(url):
            continue

        reference = payload.get("purl")
        photos.append(
            Photo(
                url=url,
                source="bing",
                title=str(payload.get("t") or ""),
                page_url=reference if is_public_image_url(reference) else None,
                is_thumbnail=url == payload.get("turl"),
            )
        )
    return unique_photos(photos)


def unique_photos(photos: list[Photo]) -> list[Photo]:
    """Сохраняет порядок и отбрасывает повторяющиеся URL."""
    seen: set[str] = set()
    result: list[Photo] = []
    for photo in photos:
        if photo.url not in seen:
            result.append(photo)
            seen.add(photo.url)
    return result


def is_blocked(page: Any) -> bool:
    """Распознаёт распространённые страницы капчи и согласия."""
    current_url = page.url.lower()
    if any(part in current_url for part in ("/sorry/", "consent.google.")):
        return True
    title = page.title().lower()
    return "unusual traffic" in title or "captcha" in title


class GoogleImagesProvider:
    """Получает превью фотографий из Google Картинок."""

    name = "google"

    def search(self, page: Any, query: str, limit: int) -> list[Photo]:
        parameters = urlencode({"q": query, "tbm": "isch", "hl": "ru"})
        page.goto(
            f"https://www.google.com/search?{parameters}",
            wait_until="domcontentloaded",
            timeout=25_000,
        )
        if is_blocked(page):
            raise SearchError("Google запросил капчу или подтверждение согласия")

        photos: list[Photo] = []
        for _ in range(5):
            # Класс Google часто меняется; запасной селектор — все изображения.
            selector = "img.YQ4gaf" if page.locator("img.YQ4gaf").count() else "img"
            raw_items = page.locator(selector).evaluate_all(
                """images => images.map(img => ({
                    src: img.currentSrc || img.getAttribute('src'),
                    data_src: img.getAttribute('data-src'),
                    alt: img.alt,
                    width: img.naturalWidth,
                    height: img.naturalHeight,
                    href: img.closest('a[href]')?.href || ''
                }))"""
            )
            photos = parse_google_images(raw_items)
            if len(photos) >= limit:
                break
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(550)

        LOGGER.info("Google Images: получено %d ссылок", len(photos))
        return photos[:limit]


class BingImagesProvider:
    """Резервный источник оригинальных URL из Bing Images."""

    name = "bing"

    def search(self, page: Any, query: str, limit: int) -> list[Photo]:
        parameters = urlencode({"q": query, "form": "HDRSC2"})
        page.goto(
            f"https://www.bing.com/images/search?{parameters}",
            wait_until="domcontentloaded",
            timeout=25_000,
        )
        if is_blocked(page):
            raise SearchError("Bing запросил капчу")

        photos: list[Photo] = []
        for _ in range(4):
            raw_items = page.locator("a.iusc[m]").evaluate_all(
                "elements => elements.map(element => element.getAttribute('m'))"
            )
            photos = parse_bing_images(raw_items)
            if len(photos) >= limit:
                break
            page.mouse.wheel(0, 1500)
            page.wait_for_timeout(550)

        LOGGER.info("Bing Images: получено %d ссылок", len(photos))
        return photos[:limit]


class HotelPhotoService:
    """Оркестрирует независимые источники; Google имеет приоритет."""

    def __init__(self, providers: list[PhotoProvider]) -> None:
        self._providers = providers

    def find(self, page: Any, hotel_name: str, limit: int) -> list[Photo]:
        query = f"{normalize_hotel_name(hotel_name)} hotel"
        collected: list[Photo] = []
        seen: set[str] = set()
        errors: list[str] = []
        successful_sources = 0

        for provider in self._providers:
            if len(collected) >= limit:
                break
            try:
                # Берём до limit у каждого источника: часть URL может совпасть.
                photos = provider.search(page, query, limit)
                successful_sources += 1
            except Exception as exc:
                # Сбой одного источника не должен отключать резервный.
                LOGGER.exception("Источник %s недоступен", provider.name)
                errors.append(f"{provider.name}: {exc}")
                continue

            for photo in photos:
                if photo.url not in seen:
                    collected.append(photo)
                    seen.add(photo.url)
                    if len(collected) == limit:
                        break

        if not collected and errors and not successful_sources:
            raise SearchError("Все источники недоступны: " + "; ".join(errors))

        return collected


class PhotoDownloader:
    """Скачивает изображения с ограничением размера и типа контента."""

    def __init__(self, output_dir: Path, timeout: int = 20) -> None:
        self._output_dir = output_dir
        self._timeout = timeout

    def download(self, photo: Photo, index: int) -> Path:
        if not is_public_image_url(photo.url):
            raise DownloadError("Недопустимый URL изображения")

        request = Request(
            photo.url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HotelPhotoParser/1.0)"},
        )
        try:
            with urlopen(request, timeout=self._timeout) as response:
                content_type = response.headers.get_content_type().lower()
                extension = IMAGE_MIME_TYPES.get(content_type)
                if not extension:
                    raise DownloadError(f"Неподдерживаемый тип: {content_type}")

                content_length = response.headers.get("Content-Length")
                if content_length and int(content_length) > MAX_IMAGE_BYTES:
                    raise DownloadError("Файл превышает лимит 15 МиБ")

                self._output_dir.mkdir(parents=True, exist_ok=True)
                path = self._output_dir / f"photo_{index:02d}{extension}"
                # Режим xb исключает случайную перезапись пользовательских файлов.
                created = False
                try:
                    with path.open("xb") as destination:
                        created = True
                        received = 0
                        while chunk := response.read(64 * 1024):
                            received += len(chunk)
                            if received > MAX_IMAGE_BYTES:
                                raise DownloadError("Файл превышает лимит 15 МиБ")
                            destination.write(chunk)
                except Exception:
                    # Удаляем только частичный файл этого вызова.
                    if created:
                        path.unlink(missing_ok=True)
                    raise

                return path
        except FileExistsError as exc:
            raise DownloadError("Файл уже существует; перезапись запрещена") from exc
        except (HTTPError, URLError, TimeoutError, OSError) as exc:
            raise DownloadError(f"Не удалось скачать изображение: {exc}") from exc
        except (ValueError, OverflowError) as exc:
            raise DownloadError(f"Некорректный HTTP-ответ: {exc}") from exc


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Фото отелей: Google Images, затем Bing Images."
    )
    parser.add_argument("hotel", help='Название отеля, например "Hilton Berlin"')
    parser.add_argument("--limit", type=int, default=10, help="От 1 до 50 фото")
    parser.add_argument("--download", action="store_true", help="Скачать фото")
    parser.add_argument("--headed", action="store_true", help="Показать браузер")
    parser.add_argument(
        "--output",
        type=Path,
        default=BASE_DIR / "photos",
        help="Родительская папка для скачанных изображений",
    )
    args = parser.parse_args(argv)
    if not 1 <= args.limit <= 50:
        parser.error("--limit должен быть от 1 до 50")
    try:
        args.hotel = normalize_hotel_name(args.hotel)
    except ValueError as exc:
        parser.error(str(exc))
    return args


def run(argv: list[str] | None = None) -> int:
    args = parse_arguments(argv)
    configure_logging()
    LOGGER.info("Начат поиск: отель=%r, limit=%d", args.hotel, args.limit)

    try:
        from playwright.sync_api import sync_playwright

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headed)
            try:
                page = browser.new_page(
                    locale="ru-RU", viewport={"width": 1280, "height": 900}
                )
                service = HotelPhotoService(
                    [GoogleImagesProvider(), BingImagesProvider()]
                )
                photos = service.find(page, args.hotel, args.limit)
            finally:
                browser.close()

        if args.download:
            destination = args.output / safe_directory_name(args.hotel)
            downloader = PhotoDownloader(destination)
            downloaded: list[Photo] = []
            for index, photo in enumerate(photos, 1):
                try:
                    saved_path = downloader.download(photo, index)
                    downloaded.append(
                        Photo(
                            url=photo.url,
                            source=photo.source,
                            title=photo.title,
                            page_url=photo.page_url,
                            is_thumbnail=photo.is_thumbnail,
                            saved_as=str(saved_path),
                        )
                    )
                except DownloadError as exc:
                    LOGGER.warning("Фото %d не скачано: %s", index, exc)
                    downloaded.append(photo)
            photos = downloaded

        output = {
            "hotel": args.hotel,
            "found": len(photos),
            "downloaded": sum(photo.saved_as is not None for photo in photos),
            "photos": [asdict(photo) for photo in photos],
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        LOGGER.info("Поиск завершён, найдено %d фото", len(photos))
        return 0
    except ImportError:
        message = "Установите зависимости: pip install -r requirements.txt"
    except Exception as exc:
        LOGGER.exception("Ошибка выполнения")
        message = str(exc)

    print(f"Ошибка: {message}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(run())
