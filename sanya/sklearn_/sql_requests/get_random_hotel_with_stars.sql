select id, name, stars
from hotels

where name is not null and stars is not null and length(stars::text) = 1 AND stars = %(stars_number)s