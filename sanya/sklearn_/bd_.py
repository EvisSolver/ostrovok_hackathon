#!/usr/bin/env python3
"""One-time/occasional import of Moscow hotels from OpenStreetMap to PostGIS.

Requires DATABASE_URL, for example:
  postgresql://user:password@localhost:5432/hotels

Install dependencies:
  pip install 'psycopg[binary]' requests
"""

import json
import os
import sys
import time

import psycopg
import requests
from psycopg.types.json import Jsonb

OVERPASS_URL = "https://overpass-api.de/api/interpreter"
QUERY = r'''[out:json][timeout:180];
area["name"="Москва"]["boundary"="administrative"]["admin_level"="4"]->.moscow;
nwr["tourism"="hotel"](area.moscow);
out center tags;'''

CREATE_SQL = """
CREATE EXTENSION IF NOT EXISTS postgis;
CREATE TABLE IF NOT EXISTS hotels (
    id BIGSERIAL PRIMARY KEY,
    osm_type TEXT NOT NULL,
    osm_id BIGINT NOT NULL,
    name TEXT,
    property_type TEXT NOT NULL DEFAULT 'hotel',
    phone TEXT,
    website TEXT,
    stars TEXT,
    rooms INTEGER,
    address JSONB NOT NULL DEFAULT '{}'::jsonb,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    geom geometry(Point, 4326) NOT NULL,
    source_url TEXT NOT NULL,
    imported_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (osm_type, osm_id)
);
CREATE INDEX IF NOT EXISTS hotels_geom_gix ON hotels USING GIST (geom);
CREATE INDEX IF NOT EXISTS hotels_name_idx ON hotels (name);
CREATE INDEX IF NOT EXISTS hotels_tags_gin ON hotels USING GIN (tags);
"""

UPSERT_SQL = """
INSERT INTO hotels (
    osm_type, osm_id, name, property_type, phone, website, stars, rooms,
    address, tags, geom, source_url, imported_at
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s,
    %s, %s,
    ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, now()
)
ON CONFLICT (osm_type, osm_id) DO UPDATE SET
    name = EXCLUDED.name,
    property_type = EXCLUDED.property_type,
    phone = EXCLUDED.phone,
    website = EXCLUDED.website,
    stars = EXCLUDED.stars,
    rooms = EXCLUDED.rooms,
    address = EXCLUDED.address,
    tags = EXCLUDED.tags,
    geom = EXCLUDED.geom,
    source_url = EXCLUDED.source_url,
    imported_at = now();
"""

ADDRESS_KEYS = (
    "addr:city", "addr:district", "addr:suburb", "addr:street",
    "addr:housenumber", "addr:postcode", "addr:full",
)


def get_data():
    headers = {"User-Agent": "MoscowHotelCatalog/1.0 (one-time OSM import)"}
    # Retry transient 429/5xx responses politely; this is intended for an
    # occasional import, not a request on every website page view.
    for attempt in range(4):
        response = requests.post(
            OVERPASS_URL,
            data={"data": QUERY},
            headers=headers,
            timeout=240,
        )
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == 3:
                response.raise_for_status()
            time.sleep(5 * (attempt + 1))
            continue
        response.raise_for_status()
        return response.json().get("elements", [])
    return []


def element_to_row(element):
    tags = element.get("tags", {})
    center = element.get("center") or element
    lat, lon = center.get("lat"), center.get("lon")
    if lat is None or lon is None:
        return None

    address = {key.removeprefix("addr:"): tags[key]
               for key in ADDRESS_KEYS if tags.get(key)}

    rooms_value = tags.get("rooms")
    try:
        rooms = int(rooms_value) if rooms_value and rooms_value.isdigit() else None
    except (AttributeError, ValueError):
        rooms = None

    osm_type = element["type"]
    osm_id = int(element["id"])
    return (
        osm_type,
        osm_id,
        tags.get("name"),
        tags.get("tourism", "hotel"),
        tags.get("phone") or tags.get("contact:phone"),
        tags.get("website") or tags.get("contact:website"),
        tags.get("stars"),
        rooms,
        Jsonb(address),
        Jsonb(tags),
        float(lon),
        float(lat),
        f"https://www.openstreetmap.org/{osm_type}/{osm_id}",
    )


def main():
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        sys.exit("Set DATABASE_URL, e.g. postgresql://user:password@localhost:5432/hotels")

    elements = get_data()
    rows = [row for item in elements if (row := element_to_row(item)) is not None]
    if not rows:
        sys.exit("No hotels returned. Check the Overpass query or Moscow admin boundary.")

    with psycopg.connect(dsn) as conn:
        conn.execute(CREATE_SQL)
        with conn.cursor() as cur:
            cur.executemany(UPSERT_SQL, rows)

    print(f"Upserted {len(rows)} OSM hotel records into hotels.")
    print("Attribution required: © OpenStreetMap contributors, ODbL 1.0")


if __name__ == "__main__":
    main()
