import { useEffect, useMemo, useRef, useState } from 'react';
import HotelCard from '../components/HotelCard.jsx';
import Filters, { EMPTY_FILTERS } from '../components/Filters.jsx';
import HotelTicker from '../components/HotelTicker.jsx';
import HeroChat from '../components/HeroChat.jsx';
import { getHotels } from '../services/hotelsService.js';
import { plural } from '../utils.js';

const PAGE_SIZE = 25;
const SORTS = {
  stars: { label: 'Сначала 5★', value: 'stars' },
  'price-asc': { label: 'Сначала дешёвые', value: 'price-asc' },
  'price-desc': { label: 'Сначала дорогие', value: 'price-desc' },
  id: { label: 'По добавлению', value: 'id' },
};

export default function HomePage() {
  const [hotels, setHotels] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(0);
  const [status, setStatus] = useState('loading'); // loading | refreshing | ok | error
  const [query, setQuery] = useState('');
  const [filters, setFilters] = useState(EMPTY_FILTERS);
  const [sort, setSort] = useState('stars');
  const [scrollProgress, setScrollProgress] = useState(0);
  const catalogRef = useRef(null);
  const requestId = useRef(0);
  const abortRef = useRef(null);

  const starsKey = filters.stars.join(',');
  const maxPrice = filters.maxPrice;

  useEffect(() => {
    const id = ++requestId.current;
    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;
    setStatus((current) => (current === 'loading' ? current : 'refreshing'));

    getHotels({ query, stars: filters.stars, maxPrice, sort, page, signal: controller.signal })
      .then((result) => {
        if (id !== requestId.current) return;
        setHotels((current) => (page === 1 ? result.items : [...current, ...result.items]));
        setTotal(result.total);
        setTotalPages(result.totalPages);
        setStatus('ok');
      })
      .catch((error) => {
        if (error.name === 'AbortError' || id !== requestId.current) return;
        setStatus('error');
      });

    return () => controller.abort();
  }, [query, starsKey, maxPrice, sort, page]);

  useEffect(() => () => abortRef.current?.abort(), []);

  useEffect(() => {
    const handleScroll = () => {
      const y = window.scrollY || 0;
      setScrollProgress(Math.min(1, Math.max(0, y / 220)));
    };
    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const cueOpacity = Math.max(0, 1 - Math.pow(scrollProgress, 2.8));
  const tickerLeft = useMemo(() => hotels.filter((_, index) => index % 2 === 0), [hotels]);
  const tickerRight = useMemo(() => hotels.filter((_, index) => index % 2 === 1), [hotels]);
  const highlight = null;

  function scrollToCatalog(e) {
    if (e) e.preventDefault();
    catalogRef.current?.scrollIntoView({ behavior: 'smooth' });
  }

  function updateFilters(next) {
    setFilters(next);
    setPage(1);
  }

  function resetCatalog() {
    setQuery('');
    setFilters(EMPTY_FILTERS);
    setSort('stars');
    setPage(1);
  }

  function handleSelectTickerHotel(tickerHotel) {
    if (tickerHotel.name) setQuery(tickerHotel.name);
    setPage(1);
    scrollToCatalog();
  }

  return (
    <div className="home-page-wrap">
      <section className="landing-hero" aria-label="Главный экран">
        <aside className="landing-hero__col landing-hero__col--left" aria-hidden="true">
          <HotelTicker hotels={tickerLeft} direction="up" stepInterval={3600} delay={0} onSelectHotel={handleSelectTickerHotel} />
        </aside>

        <div className="landing-hero__center">
          <HeroChat filters={filters} query={query} onSelectHotel={() => {}} />
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

        <aside className="landing-hero__col landing-hero__col--right" aria-hidden="true">
          <HotelTicker hotels={tickerRight} direction="down" stepInterval={3600} delay={1800} onSelectHotel={handleSelectTickerHotel} />
        </aside>
      </section>

      <section id="catalog" ref={catalogRef} className="catalog-section" aria-label="Каталог отелей">
        <div className="container">
          <div className="catalog-section__head">
            <div>
              <h2>Каталог и поиск доступных отелей</h2>
              <p className="muted">Поиск выполняется в базе данных. Показываем по 25 отелей за раз.</p>
            </div>
          </div>

          <div className="catalog-search">
            <form className="catalog-search__form" onSubmit={(e) => e.preventDefault()}>
              <div className="catalog-search__field">
                <svg className="catalog-search__icon" viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                  <circle cx="11" cy="11" r="8"></circle><line x1="21" y1="2" x2="16.65" y2="16.65"></line>
                </svg>
                <input
                  value={query}
                  onChange={(e) => { setQuery(e.target.value); setPage(1); }}
                  placeholder="Поиск по названию отеля…"
                  aria-label="Поиск по названию отеля"
                />
                {query && <button type="button" className="catalog-search__clear" onClick={() => { setQuery(''); setPage(1); }} title="Очистить поиск">×</button>}
              </div>
              <button type="submit" className="btn btn--orange catalog-search__btn">Найти</button>
            </form>
          </div>

          <div className="home">
            <Filters value={filters} onChange={updateFilters} cities={[]} priceMax={50000} />
            <div className="results">
              <div className="results__bar">
                <p>{status === 'ok' || status === 'refreshing' ? `Показано ${hotels.length} из ${total} ${plural(total, 'отеля', 'отелей', 'отелей')}` : ' '}</p>
                <label>
                  Сортировка
                  <select value={sort} onChange={(e) => { setSort(e.target.value); setPage(1); }}>
                    {Object.entries(SORTS).map(([key, option]) => <option key={key} value={option.value}>{option.label}</option>)}
                  </select>
                </label>
              </div>

              {status === 'loading' && <p className="muted">Загрузка первой пачки отелей…</p>}
              {status === 'refreshing' && <p className="muted">Обновляем результаты…</p>}
              {status === 'error' && <p className="muted">Не удалось выполнить поиск в каталоге. Попробуйте ещё раз.</p>}
              {status === 'ok' && total === 0 && (
                <div className="catalog-empty">
                  <p className="muted">Ничего не найдено по заданным параметрам.</p>
                  <button type="button" className="btn btn--orange" onClick={resetCatalog}>Сбросить фильтры и поиск</button>
                </div>
              )}
              <div className="list">{hotels.map((hotel) => <HotelCard key={hotel.slug} hotel={hotel} highlight={highlight} />)}</div>
              {status !== 'loading' && page < totalPages && (
                <button type="button" className="btn btn--orange" onClick={() => setPage((current) => current + 1)} disabled={status === 'refreshing'}>
                  {status === 'refreshing' ? 'Загрузка…' : 'Показать ещё 25'}
                </button>
              )}
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
