import json, hashlib, random, re, math

SRC = "hotels.json"
DST = "moscow_hotels_priced.json"
TODAY = "2026-10-26"
KREMLIN = (55.75204, 37.61730)

def seed_of(el):
    key = f'{el["type"]}/{el["id"]}'
    return int(hashlib.md5(key.encode()).hexdigest()[:12], 16)

def stars_of(tags):
    raw = tags.get("stars")
    if not raw:
        return None
    nums = [int(x) for x in re.findall(r"\d+", raw)]
    return min(nums) if nums else None   # "3;4" -> 3

def dist_km(lat, lon):
    R = 6371.0
    p1, p2 = math.radians(lat), math.radians(KREMLIN[0])
    dl = math.radians(lon - KREMLIN[1])
    a = math.sin((p2-p1)/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * R * math.asin(math.sqrt(a))

def location_factor(el):
    if "lat" in el:
        lat, lon = el["lat"], el["lon"]
    elif "center" in el:
        lat, lon = el["center"]["lat"], el["center"]["lon"]
    else:
        return 1.0
    d = dist_km(lat, lon)
    if d < 3:  return 1.35   # центр
    if d < 8:  return 1.10
    if d < 15: return 0.95
    return 0.85             # замкадье

def rnd(seed, lo, hi, step):
    a, b = lo // step, hi // step
    if b < a:
        a, b = b, a
    return random.Random(seed).randint(a, b) * step

def base_range(tags):
    t = tags.get("tourism")
    s = stars_of(tags)

    if t == "hostel":
        if tags.get("hotel") == "capsule":
            lo, hi, step = 1200, 2600, 100
        else:
            lo, hi, step = 600, 1600, 50
        if s and s >= 3:
            lo, hi = lo * 2, hi * 2
        return lo, hi, step, "per_bed"

    if t == "guest_house":
        return 2500, 6500, 100, "per_night"

    if t == "apartment":
        return 3000, 9000, 100, "per_night"

    if t == "hotel":
        if tags.get("amenity") == "love_hotel":
            return 1500, 3500, 100, "per_night"
        if tags.get("hotel") == "apartment_hotel":
            return 3500, 8000, 100, "per_night"
        if s == 5: return 15000, 32000, 500, "per_night"
        if s == 4: return 8500, 16000, 500, "per_night"
        if s == 3: return 5000, 9000, 250, "per_night"
        if s == 2: return 3200, 5500, 100, "per_night"
        if s == 1: return 2200, 3600, 100, "per_night"
        return 2800, 6500, 100, "per_night"   # без звёзд

    return None

with open(SRC, encoding="utf-8") as f:
    data = json.load(f)

priced = skipped = 0

for el in data["elements"]:
    tags = el.get("tags") or {}
    rng = base_range(tags)
    if rng is None:
        continue
    if "mock:price:min" in tags:      # идемпотентность
        skipped += 1
        continue

    lo, hi, step, unit = rng
    mid = (lo + hi) // 2
    sd  = seed_of(el)
    fk  = location_factor(el)

    mn = round(rnd(sd, lo, mid, step) * fk / step) * step
    mx = round(rnd(sd ^ 0x5BF03635, mid, hi, step) * fk / step) * step
    if mx < mn:
        mx = mn + step
    av = round((mn + mx) / 2 / step) * step

    tags.update({
        "mock:price:min":      str(mn),
        "mock:price:max":      str(mx),
        "mock:price:avg":      str(av),
        "mock:price:currency": "RUB",
        "mock:price:unit":     unit,
        "mock:price:source":   "synthetic-mock",
        "mock:price:updated":  TODAY,
    })
    priced += 1

with open(DST, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"priced: {priced}, already had price: {skipped}")