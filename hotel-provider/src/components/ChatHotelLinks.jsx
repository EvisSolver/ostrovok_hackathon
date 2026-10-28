import { Link } from 'react-router-dom';
import Stars from './Stars.jsx';
import { formatPrice, plural } from '../utils.js';

/**
 * Подборка отелей под ответом ИИ — «листок», который помощник кладёт рядом с ответом.
 * hotels — из события `done` сервера (ID из JSON нейронки уже заменены на данные из базы):
 *   [{ slug, name, stars, priceFrom, snippet, marks: [{ kind, name, distance }] }]
 * variant: 'sheet' — крупный чат на главной, 'inline' — компактный виджет.
 */
export default function ChatHotelLinks({ hotels, variant = 'sheet', onSelect }) {
  if (!hotels?.length) return null;
  const n = hotels.length;
  return (
    <section className={`chat-shortlist chat-shortlist--${variant}`} aria-label="Подобранные отели">
      <header className="chat-shortlist__head">
        <span>Подборка помощника</span>
        <span className="chat-shortlist__count">{n} {plural(n, 'отель', 'отеля', 'отелей')}</span>
      </header>
      <ol className="chat-shortlist__list">
        {hotels.map((h) => (
          <li key={h.slug}>
            <Link to={`/hotels/${h.slug}`} className="chat-shortlist__row" onClick={() => onSelect?.(h.slug)}>
              <div className="chat-shortlist__main">
                {h.stars > 0 && (
                  <div className="chat-shortlist__stars">
                    <Stars count={h.stars} />
                    <span>{h.stars} {plural(h.stars, 'звезда', 'звезды', 'звёзд')}</span>
                  </div>
                )}
                <h4 className="chat-shortlist__name">{h.name}</h4>
                {h.snippet && <p className="chat-shortlist__snippet">{h.snippet}</p>}
                {h.marks?.length > 0 && (
                  <ul className="chat-shortlist__marks">
                    {h.marks.map((m) => (
                      <li key={`${m.kind}-${m.name}`} title={MARK_TITLE[m.kind] ?? 'Рядом'}>
                        <MarkIcon kind={m.kind} />
                        <span className="chat-shortlist__mark-name">{m.name}</span>
                        {m.distance && <span className="chat-shortlist__mark-dist">{m.distance}</span>}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
              <div className="chat-shortlist__side">
                {h.priceFrom != null ? (
                  <span className="chat-shortlist__price"><small>от</small> <strong>{formatPrice(h.priceFrom, 'RUB')}</strong> <small>/ ночь</small></span>
                ) : (
                  <span className="chat-shortlist__price chat-shortlist__price--none">Цена по запросу</span>
                )}
                <span className="chat-shortlist__go">Смотреть <span aria-hidden="true">→</span></span>
              </div>
            </Link>
          </li>
        ))}
      </ol>
    </section>
  );
}

const MARK_TITLE = {
  attraction: 'Достопримечательность рядом',
  park: 'Парк рядом',
  water: 'Вода рядом',
  river: 'Река рядом',
};

/** Иконки пометок одним штрихом: достопримечательность, парк, вода. */
function MarkIcon({ kind }) {
  const common = { width: 14, height: 14, viewBox: '0 0 16 16', fill: 'none', stroke: 'currentColor', strokeWidth: 1.6, strokeLinecap: 'round', strokeLinejoin: 'round', 'aria-hidden': true };
  if (kind === 'park') {
    return (
      <svg {...common}>
        <path d="M8 2.5 4.5 8h2L4 11.5h8L9.5 8h2z" />
        <path d="M8 11.5V14" />
      </svg>
    );
  }
  if (kind === 'water' || kind === 'river') {
    return (
      <svg {...common}>
        <path d="M2 6c1.5 0 1.5-1.2 3-1.2S6.5 6 8 6s1.5-1.2 3-1.2S12.5 6 14 6" />
        <path d="M2 10.5c1.5 0 1.5-1.2 3-1.2s1.5 1.2 3 1.2 1.5-1.2 3-1.2 1.5 1.2 3 1.2" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M3 13.5h10" />
      <path d="M4.5 13.5V7M8 13.5V7M11.5 13.5V7" />
      <path d="M2.5 7 8 3l5.5 4z" />
    </svg>
  );
}
