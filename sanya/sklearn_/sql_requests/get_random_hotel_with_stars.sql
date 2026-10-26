select id, name, stars
from hotels

where name is not null and stars is not null and length(stars) = 1
order by random()

limit 1