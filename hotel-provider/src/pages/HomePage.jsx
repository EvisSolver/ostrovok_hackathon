import { useEffect, useMemo, useState } from 'react';
import HotelCard from '../components/HotelCard.jsx';
import Filters, { EMPTY_FILTERS } from '../components/Filters.jsx';
import { getHotels } from '../services/hotelsService.js';
import { ACCESS, plural } from '../utils.js';

const BIG = 1e9; // отели без показателя уходят в конец списка
const SORTS = {
  default: { label: 'Рекомендуемые', fn: (a, b) => (b.rating ?? 0) - (a.rating ?? 0) },
  'price-asc': { label: 'Сначала дешёвые', fn: (a, b) => a.priceFrom - b.priceFrom },
  'price-desc': { label: 'Сначала дорогие', fn: (a, b) => b.priceFrom - a.priceFrom },
  stars: { label: 'По звёздам', fn: (a, b) => b.stars - a.stars },
  metro: { label: ACCESS.metro.sort, fn: (a, b) => (a.access.metro ?? BIG) - (b.access.metro ?? BIG) },
  sea: { label: ACCESS.sea.sort, fn: (a, b) => (a.access.sea ?? BIG) - (b.access.sea ?? BIG) },
  center: { label: ACCESS.center.sort, fn: (a, b) => (a.access.center ?? BIG) - (b.access.center ?? BIG) },
};

export default function HomePage() {
  const [hotels, setHotels] = useState([]);
  const [status, setStatus] = useState('loading'); // loading | ok | error
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sort, setSort] = useState('default');

  useEffect(() => {
    getHotels().then((h) => { setHotels(h); setStatus('ok'); }).catch(() => setStatus('error'));
  }, []);

  const cities = useMemo(() => [...new Set(hotels.map((h) => h.city))].sort(), [hotels]);
  const priceMax = useMemo(() => Math.max(1000, Math.ceil(Math.max(0, ...hotels.map((h) => h.priceFrom)) / 500) * 500), [hotels]);

  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    const f = filters;
    return hotels
      .filter((h) => !q || `${h.name} ${h.city} ${h.region}`.toLowerCase().includes(q))
      .filter((h) => !f.city || h.city === f.city)
      .filter((h) => !f.stars.length || f.stars.includes(h.stars))
      .filter((h) => f.maxPrice == null || h.priceFrom <= f.maxPrice)
      .filter((h) => ['metro', 'sea', 'center'].every((k) => f[k] == null || (h.access[k] != null && h.access[k] <= f[k])))
      .sort(SORTS[sort].fn);
  }, [hotels, query, filters, sort]);

  const highlight = ['metro', 'sea', 'center'].includes(sort) ? sort : null;

  return (
    <>
      <section className="hero">
        <div className="container">
          <h1>Отели России</h1>
          <form className="search" onSubmit={(e) => e.preventDefault()}>
            <input value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Город или название отеля" aria-label="Поиск" />
            <button type="submit" className="btn btn--orange">Найти</button>
          </form>
        </div>
      </section>

      <div className="container home">
        <Filters value={filters} onChange={setFilters} cities={cities} priceMax={priceMax} />

        <section className="results">
          <div className="results__bar">
            <p>{status === 'ok' ? `Найдено ${list.length} ${plural(list.length, 'отель', 'отеля', 'отелей')}` : ' '}</p>
            <label>Сортировка
              <select value={sort} onChange={(e) => setSort(e.target.value)}>
                {Object.entries(SORTS).map(([k, s]) => <option key={k} value={k}>{s.label}</option>)}
              </select>
            </label>
          </div>

          {status === 'loading' && <p className="muted">Загрузка…</p>}
          {status === 'error' && <p className="muted">Не удалось загрузить отели. Проверьте файл public/data/hotels.json.</p>}
          {status === 'ok' && list.length === 0 && <p className="muted">Ничего не найдено. Измените фильтры или нажмите «Сбросить».</p>}
          <div className="list">{list.map((h) => <HotelCard key={h.slug} hotel={h} highlight={highlight} />)}</div>
        </section>
      </div>
    </>
  );
}
