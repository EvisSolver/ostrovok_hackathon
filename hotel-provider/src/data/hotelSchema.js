import { walkMinutes } from '../utils.js';

/**
 * Формат отеля в public/data/hotels.json (поля, помеченные *, нужны для карточки):
 *   slug*, name*, city*, region, country, stars*, priceFrom*, currency* ('RUB'), cover, rating, reviewsCount, tagline,
 *   lat, lon                — координаты отеля (из карт)
 *   access {metro, sea, center} — минуты пешком; null = нет рядом
 *   places {metro:[{name,lat,lon}], sea:[...], center:[...]} — точки из карт (OSM/Overpass);
 *       если access.<ключ> не задан, берётся ближайшая точка и время считается по координатам
 *   theme.accent, gallery[], description[], highlights[], amenities[], rooms[], location{address},
 *   reviews[], contacts{}, policies[]
 */
const KEYS = ['metro', 'sea', 'center'];

function computeAccess(raw) {
  const access = { metro: null, sea: null, center: null, ...(raw.access || {}) };
  if (raw.lat == null || raw.lon == null) return access;
  for (const k of KEYS) {
    const pts = raw.places?.[k];
    if (access[k] == null && pts?.length) {
      access[k] = Math.min(...pts.map((p) => walkMinutes(raw, p)));
    }
  }
  return access;
}

export function normalizeHotel(raw = {}) {
  return {
    cover: '', tagline: '', city: '', region: '', country: 'Россия', currency: 'RUB',
    rating: null, reviewsCount: 0,
    gallery: [], description: [], highlights: [], amenities: [], rooms: [], reviews: [], policies: [],
    location: null, contacts: null, theme: null,
    ...raw,
    access: computeAccess(raw),
  };
}
