SELECT id, name FROM hotels
WHERE name is not null
ORDER BY random()
LIMIT 1