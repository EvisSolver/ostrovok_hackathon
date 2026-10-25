export function formatPrice(value, currency = 'RUB') {
  if (value == null) return '';
  return new Intl.NumberFormat('ru-RU', { style: 'currency', currency, maximumFractionDigits: 0 }).format(value);
}

/** Подписи для географических показателей (минуты пешком). */
export const ACCESS = {
  metro: { short: 'до метро', sort: 'Ближе к метро' },
  sea: { short: 'до моря', sort: 'Ближе к морю' },
  center: { short: 'до центра', sort: 'Ближе к центру' },
};

export function plural(n, one, few, many) {
  const m10 = n % 10, m100 = n % 100;
  if (m10 === 1 && m100 !== 11) return one;
  if (m10 >= 2 && m10 <= 4 && (m100 < 10 || m100 >= 20)) return few;
  return many;
}

/** Время пешком по прямой между двумя точками (с поправкой на изгибы улиц), минуты. */
export function walkMinutes(a, b) {
  const R = 6371000, rad = (x) => (x * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat), dLon = rad(b.lon - a.lon);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLon / 2) ** 2;
  const meters = 2 * R * Math.asin(Math.sqrt(h));
  return Math.max(1, Math.round((meters * 1.3) / 80)); // ~80 м/мин
}
