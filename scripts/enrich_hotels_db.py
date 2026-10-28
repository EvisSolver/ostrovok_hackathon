"""Import existing mock prices and stable descriptions into hotels.

Run from the repository root. Existing non-null prices and descriptions are kept.
"""

import asyncio
import hashlib
import json
import os
from pathlib import Path

import asyncpg

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "moscow_hotels_priced.json"
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://otters:hackathon@localhost:5432/otters_db",
)
INTRODUCTIONS = (
    "Спокойный вариант для городской поездки с удобной отправной точкой для прогулок.",
    "Практичная база для знакомства с городом: после насыщенного дня здесь легко переключиться на отдых.",
    "Подходит для тех, кто ценит городской ритм, интересные места и комфортную остановку.",
    "Хороший выбор для короткой поездки и размеренного отдыха с городскими маршрутами поблизости.",
)
SURROUNDINGS = (
    "В окрестностях есть зелёные зоны и городские маршруты для прогулок.",
    "Локация сочетает городскую инфраструктуру с прогулочными и природными местами.",
    "Вокруг есть точки для прогулок, покупок и знакомства с городом.",
    "Рядом сочетаются городская жизнь и места для отдыха.",
)


def description_for(hotel_id: int, name: str, stars: int | None) -> str:
    digest = hashlib.sha256(f"{hotel_id}:{name}:{stars or 0}".encode()).digest()
    intro = INTRODUCTIONS[digest[0] % len(INTRODUCTIONS)]
    surrounding = SURROUNDINGS[digest[1] % len(SURROUNDINGS)]
    category = f"{stars}-звёздочный отель" if stars else "отель"
    return f"{intro} {surrounding} {name} — {category} для самостоятельных путешественников."


def parse_record(element: dict) -> tuple[int, int, str] | None:
    tags = element.get("tags") or {}
    average = tags.get("mock:price:avg")
    name = tags.get("name")
    if average is None or not name:
        return None
    stars_raw = str(tags.get("stars") or "").split(";")[0]
    stars = int(stars_raw) if stars_raw.isdigit() else None
    hotel_id = int(element["id"])
    return hotel_id, int(average), description_for(hotel_id, name, stars)


async def main() -> None:
    source_data = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = [
        record
        for element in source_data.get("elements", [])
        if (record := parse_record(element)) is not None
    ]
    if not records:
        raise RuntimeError(f"No mock prices found in {SOURCE}")

    connection = await asyncpg.connect(DATABASE_URL)
    try:
        async with connection.transaction():
            await connection.execute(
                "ALTER TABLE hotels ADD COLUMN IF NOT EXISTS description TEXT"
            )
            matched_rows = 0
            for hotel_id, price, description in records:
                result = await connection.execute(
                    """
                    UPDATE hotels
                    SET price = COALESCE(price, $2),
                        description = COALESCE(NULLIF(btrim(description), ''), $3)
                    WHERE id = $1
                    """,
                    hotel_id,
                    price,
                    description,
                )
                if result.endswith("1"):
                    matched_rows += 1
        matched = await connection.fetchval(
            "SELECT count(*) FROM hotels WHERE price IS NOT NULL AND description IS NOT NULL"
        )
        print(f"Source records: {len(records)}")
        print(f"Rows matched: {matched_rows}; existing prices and descriptions were preserved")
        print(f"Hotels with both price and description: {matched}")
    finally:
        await connection.close()


if __name__ == "__main__":
    asyncio.run(main())
