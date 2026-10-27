import { useEffect, useMemo, useRef, useState } from 'react';
import HotelCard from '../components/HotelCard.jsx';
import Filters, { EMPTY_FILTERS } from '../components/Filters.jsx';
import HotelTicker from '../components/HotelTicker.jsx';
import HeroChat from '../components/HeroChat.jsx';
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
  const [scrollProgress, setScrollProgress] = useState(0);
  const catalogRef = useRef(null);

  useEffect(() => {
    getHotels()
      .then((h) => {
        setHotels(h);
        setStatus('ok');
      })
      .catch(() => setStatus('error'));
  }, []);

  // Отслеживание скролла для плавного исчезновения плашки с ускорением к концу
  useEffect(() => {
    const handleScroll = () => {
      const y = window.scrollY || 0;
      const maxDistance = 220; // Дистанция скролла для полного исчезновения
      const progress = Math.min(1, Math.max(0, y / maxDistance));
      setScrollProgress(progress);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // Прогрессивное исчезновение с ускорением к концу (степенная кривая ease-in: 1 - progress^2.8)
  const cueOpacity = Math.max(0, 1 - Math.pow(scrollProgress, 2.8));

  const cities = useMemo(() => [...new Set(hotels.map((h) => h.city))].sort(), [hotels]);
  const priceMax = useMemo(
    () => Math.max(1000, Math.ceil(Math.max(0, ...hotels.map((h) => h.priceFrom)) / 500) * 500),
    [hotels]
  );

  const list = useMemo(() => {
    const q = query.trim().toLowerCase();
    const f = filters;
    return hotels
      .filter((h) => !q || `${h.name} ${h.city} ${h.region}`.toLowerCase().includes(q))
      .filter((h) => !f.city || h.city === f.city)
      .filter((h) => !f.stars.length || f.stars.includes(h.stars))
      .filter((h) => f.maxPrice == null || h.priceFrom <= f.maxPrice)
      .filter((h) =>
        ['metro', 'sea', 'center'].every(
          (k) => f[k] == null || (h.access[k] != null && h.access[k] <= f[k])
        )
      )
      .sort(SORTS[sort].fn);
  }, [hotels, query, filters, sort]);

  const highlight = ['metro', 'sea', 'center'].includes(sort) ? sort : null;
  const tickerHotels = useMemo(() => hotels.filter((hotel) => hotel.slug), [hotels]);
  const tickerLeft = useMemo(() => tickerHotels.filter((_, index) => index % 2 === 0), [tickerHotels]);
  const tickerRight = useMemo(() => tickerHotels.filter((_, index) => index % 2 === 1), [tickerHotels]);

  function scrollToCatalog(e) {
    if (e) e.preventDefault();
    catalogRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  function handleSelectTickerHotel(tickerHotel) {
    const existing = hotels.find((h) => h.slug === tickerHotel.slug);
    if (existing) {
      setQuery(existing.name);
    } else if (tickerHotel.city) {
      setFilters((prev) => ({ ...prev, city: tickerHotel.city }));
    }
    scrollToCatalog();
  }

  return (
    <div className="home-page-wrap">
      {/* 1. Первый экран: Столбики отелей слева и справа (идут рывком), по центру сквозной чат */}
      <section className="landing-hero" aria-label="Главный экран">
        {/* Левая колонка отелей из каталога БД */}
        <aside className="landing-hero__col landing-hero__col--left" aria-hidden="true">
          <HotelTicker
            hotels={tickerLeft}
            direction="up"
            stepInterval={3600}
            delay={0}
            onSelectHotel={handleSelectTickerHotel}
          />
        </aside>

        {/* Центральный блок: чат с невидимо передаваемыми фильтрами */}
        <div className="landing-hero__center">
          <HeroChat
            filters={filters}
            query={query}
            onSelectHotel={() => {}}
          />

          {/* Плашка «Листайте вниз к каталогу и фильтрам» — исчезает с ускорением к концу */}
          <a
            href="#catalog"
            className="landing-hero__scroll-cue"
            onClick={scrollToCatalog}
            title="Перейти к поиску и каталогу"
            style={{
              opacity: cueOpacity,
              pointerEvents: cueOpacity < 0.05 ? 'none' : 'auto',
              transform: `translateY(${scrollProgress * 8}px)`,
              transition: 'box-shadow 0.2s ease',
            }}
          >
            <span>Листайте вниз к каталогу и фильтрам</span>
            <span className="landing-hero__scroll-arrow">↓</span>
          </a>
        </div>

        {/* Правая колонка отелей из каталога БД */}
        <aside className="landing-hero__col landing-hero__col--right" aria-hidden="true">
          <HotelTicker
            hotels={tickerRight}
            direction="down"
            stepInterval={3600}
            delay={1800}
            onSelectHotel={handleSelectTickerHotel}
          />
        </aside>
      </section>

      {/* 2. Листаешь вниз: поиск, фильтрация, список доступных отелей */}
      <section id="catalog" ref={catalogRef} className="catalog-section" aria-label="Каталог отелей">
        <div className="container">
          <div className="catalog-section__head">
            <div>
              <h2>Каталог и поиск доступных отелей</h2>
              <p className="muted">
                Используйте быстрый поиск по городам или настройте фильтры под ваши даты и бюджет
              </p>
            </div>
          </div>

          {/* Поисковая строка в начале каталога */}
          <div className="catalog-search">
            <form className="catalog-search__form" onSubmit={(e) => e.preventDefault()}>
              <div className="catalog-search__field">
                <svg
                  className="catalog-search__icon"
                  viewBox="0 0 24 24"
                  width="20"
                  height="20"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                >
                  <circle cx="11" cy="11" r="8"></circle>
                  <line x1="21" y1="2" x2="16.65" y2="16.65"></line>
                </svg>
                <input
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder="Поиск по названию отеля, городу или региону (например: Сочи, Тверская, Москва)..."
                  aria-label="Поиск по каталогу отелей"
                />
                {query && (
                  <button
                    type="button"
                    className="catalog-search__clear"
                    onClick={() => setQuery('')}
                    title="Очистить поиск"
                  >
                    ×
                  </button>
                )}
              </div>
              <button type="submit" className="btn btn--orange catalog-search__btn">
                Найти
              </button>
            </form>

            {/* Быстрые фильтры городов */}
            <div className="catalog-search__quick-cities">
              <span className="muted">Города:</span>
              <button
                type="button"
                className={`catalog-search__city-pill ${!filters.city ? 'is-active' : ''}`}
                onClick={() => setFilters((f) => ({ ...f, city: '' }))}
              >
                Все города
              </button>
              {cities.map((c) => (
                <button
                  key={c}
                  type="button"
                  className={`catalog-search__city-pill ${filters.city === c ? 'is-active' : ''}`}
                  onClick={() => setFilters((f) => ({ ...f, city: c }))}
                >
                  {c}
                </button>
              ))}
            </div>
          </div>

          {/* Фильтры + Список отелей */}
          <div className="home">
            <Filters
              value={filters}
              onChange={setFilters}
              cities={cities}
              priceMax={priceMax}
            />

            <div className="results">
              <div className="results__bar">
                <p>
                  {status === 'ok'
                    ? `Найдено ${list.length} ${plural(list.length, 'отель', 'отеля', 'отелей')}`
                    : ' '}
                </p>
                <label>
                  Сортировка
                  <select value={sort} onChange={(e) => setSort(e.target.value)}>
                    {Object.entries(SORTS).map(([k, s]) => (
                      <option key={k} value={k}>
                        {s.label}
                      </option>
                    ))}
                  </select>
                </label>
              </div>

              {status === 'loading' && <p className="muted">Загрузка отелей…</p>}
              {status === 'error' && (
                <p className="muted">
                  Не удалось загрузить отели. Проверьте файл public/data/hotels.json.
                </p>
              )}
              {status === 'ok' && list.length === 0 && (
                <div className="catalog-empty">
                  <p className="muted">Ничего не найдено по заданным параметрам.</p>
                  <button
                    type="button"
                    className="btn btn--orange"
                    onClick={() => {
                      setQuery('');
                      setFilters(EMPTY_FILTERS);
                    }}
                  >
                    Сбросить фильтры и поиск
                  </button>
                </div>
              )}
              <div className="list">
                {list.map((h) => (
                  <HotelCard key={h.slug} hotel={h} highlight={highlight} />
                ))}
              </div>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
