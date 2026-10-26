
####
import psycopg2

sql = """
SELECT h.id, h.name,
       w.name       AS water_name,
       w.type       AS water_type,
       w.distance_m AS water_m,
       a.name       AS attraction_name,
       a.distance_m AS attraction_m
FROM hotels h
JOIN LATERAL (
    SELECT gz.name, gz.type,
           ST_Distance(h.location, gz.location) AS distance_m
    FROM green_zones gz
    WHERE gz.type IN ('water', 'river')
      AND ST_DWithin(h.location, gz.location, 500)
    ORDER BY gz.location <-> h.location
    LIMIT 1
) w ON true
JOIN LATERAL (
    SELECT a.name,
           ST_Distance(h.location, a.location) AS distance_m
    FROM attraction a
    WHERE ST_DWithin(h.location, a.location, 500)
    ORDER BY a.location <-> h.location
    LIMIT 1
) a ON true
ORDER BY w.distance_m;
"""

conn = psycopg2.connect(host="localhost", port=5432,
                        user="otters", password="hackathon", dbname="otters_db")
cur = conn.cursor()
cur.execute(sql)

for n, (hid, hname, wname, wtype, wdist, aname, adist) in enumerate(cur, 1):
    print(f"\n{n:>3}. {hname}  (id={hid})")
    print(f"     💧 [{wtype:<6}] {wname or '—':<28} {wdist:7.0f} м")
    print(f"     🏛  {'':<8} {aname or '—':<28} {adist:7.0f} м")

cur.close()
conn.close()