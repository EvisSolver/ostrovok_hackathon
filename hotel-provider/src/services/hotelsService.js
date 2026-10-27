import { normalizeHotel } from '../data/hotelSchema.js';

/** Единственная точка доступа сайта к каталогу отелей из PostgreSQL. */
let cache = null;

export async function getHotels() {
  if (!cache) {
    const res = await fetch('/api/hotels');
    if (!res.ok) throw new Error('Не удалось загрузить каталог отелей');
    cache = (await res.json()).map(normalizeHotel);
  }
  return cache;
}

export async function getHotelBySlug(slug) {
  const res = await fetch(`/api/hotels/${encodeURIComponent(slug)}`);
  if (res.status === 404) return null;
  if (!res.ok) throw new Error('Не удалось загрузить отель');
  return normalizeHotel(await res.json());
}
