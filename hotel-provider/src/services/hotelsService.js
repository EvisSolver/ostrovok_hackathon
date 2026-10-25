import { normalizeHotel } from '../data/hotelSchema.js';

/**
 * ЕДИНАЯ ТОЧКА ДОСТУПА К ДАННЫМ.
 * Сейчас читается public/data/hotels.json. Замените URL или тело getHotels() на свой источник.
 */
let cache = null;

export async function getHotels() {
  if (!cache) {
    const res = await fetch(`${import.meta.env.BASE_URL}data/hotels.json`);
    if (!res.ok) throw new Error('Не удалось загрузить данные об отелях');
    cache = (await res.json()).map(normalizeHotel);
  }
  return cache;
}

export async function getHotelBySlug(slug) {
  return (await getHotels()).find((h) => h.slug === slug) ?? null;
}
