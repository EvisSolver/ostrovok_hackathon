import { normalizeHotel } from '../data/hotelSchema.js';

const PAGE_SIZE = 25;

/** Fetch one bounded page from the PostgreSQL-backed catalog. */
export async function getHotels({
  query = '',
  stars = [],
  maxPrice = null,
  sort = 'stars',
  page = 1,
  proximity = {},
  signal,
} = {}) {
  const params = new URLSearchParams({
    page: String(page),
    page_size: String(PAGE_SIZE),
    sort,
  });
  if (query.trim()) params.set('q', query.trim());
  if (stars.length) params.set('stars', stars.join(','));
  if (maxPrice != null) params.set('max_price', String(maxPrice));
  Object.entries(proximity).forEach(([key, value]) => {
    if (value != null) params.set(`${key}_distance_m`, String(value));
  });

  const res = await fetch(`/api/hotels?${params}`, { signal });
  if (!res.ok) throw new Error('Не удалось загрузить каталог отелей');
  const result = await res.json();
  return { ...result, items: result.items.map(normalizeHotel) };
}

export async function getHotelBySlug(slug) {
  const res = await fetch(`/api/hotels/${encodeURIComponent(slug)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Не удалось загрузить отель');
  return normalizeHotel(await res.json());
}
