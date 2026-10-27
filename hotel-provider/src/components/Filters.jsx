export const EMPTY_FILTERS = { city: '', stars: [], maxPrice: null, metro: null, sea: null, center: null };
const MINUTES = [5, 10, 15, 30];

export default function Filters({ value, onChange, cities, priceMax }) {
  const set = (patch) => onChange({ ...value, ...patch });
  const toggleStar = (n) => set({ stars: value.stars.includes(n) ? value.stars.filter((s) => s !== n) : [...value.stars, n] });
  const price = value.maxPrice ?? priceMax;

  return (
    <aside className="filters">
      <div className="filters__head">
        <h2>Фильтры</h2>
        <button type="button" className="link-btn" onClick={() => onChange(EMPTY_FILTERS)}>Сбросить</button>
      </div>

      <fieldset>
        <legend>Цена за ночь до {price.toLocaleString('ru-RU')} ₽</legend>
        <input type="range" min={1000} max={priceMax} step={500} value={price}
               onChange={(e) => set({ maxPrice: Number(e.target.value) >= priceMax ? null : Number(e.target.value) })} />
      </fieldset>

      <fieldset>
        <legend>Звёзды</legend>
        <div className="star-pick">
          {[5, 4, 3, 2, 1].map((n) => (
            <button type="button" key={n} className={value.stars.includes(n) ? 'is-on' : ''} onClick={() => toggleStar(n)}>{n} ★</button>
          ))}
        </div>
      </fieldset>

    </aside>
  );
}
