export const EMPTY_FILTERS = {
  stars: [],
  maxPrice: null,
  parkDistanceM: null,
  waterDistanceM: null,
  riverDistanceM: null,
  roadDistanceM: null,
  attractionDistanceM: null,
  mallDistanceM: null,
  foodDistanceM: null,
};

const DISTANCES = [250, 500, 1000, 2000];
const PROXIMITY_FILTERS = [
  ['parkDistanceM', 'Парк'],
  ['waterDistanceM', 'Водоём'],
  ['riverDistanceM', 'Река'],
  ['roadDistanceM', 'Дорога'],
  ['attractionDistanceM', 'Достопримечательность'],
  ['mallDistanceM', 'Торговый центр'],
  ['foodDistanceM', 'Место поесть'],
];

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

      <fieldset>
        <legend>Что рядом</legend>
        <p className="filters__hint">Показываем отели, рядом с которыми есть объект из базы — в радиусе до выбранного расстояния.</p>
        <div className="near-pick">
          {PROXIMITY_FILTERS.map(([key, label]) => (
            <div className="near-pick__row" key={key}>
              <span className="near-pick__label">{label}</span>
              <div className="near-pick__chips">
                <button
                  type="button"
                  className={value[key] == null ? 'is-on' : ''}
                  onClick={() => set({ [key]: null })}
                >
                  любое
                </button>
                {DISTANCES.map((meters) => (
                  <button
                    type="button"
                    key={meters}
                    className={value[key] === meters ? 'is-on' : ''}
                    onClick={() => set({ [key]: meters })}
                  >
                    {meters < 1000 ? `${meters} м` : `${meters / 1000} км`}
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </fieldset>

    </aside>
  );
}
