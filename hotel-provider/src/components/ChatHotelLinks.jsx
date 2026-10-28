import { Link } from 'react-router-dom';

/**
 * Ссылки на отели под ответом ИИ.
 * hotels — из события `done` сервера: [{ slug, name, stars, priceFrom? }]
 * (сервер уже заменил ID из JSON нейронки на настоящие названия из базы).
 * variant: 'pill' — крупный чат на главной, 'inline' — компактный виджет.
 */
export default function ChatHotelLinks({ hotels, variant = 'pill', onSelect }) {
  if (!hotels?.length) return null;
  const isPill = variant === 'pill';
  return (
    <div className={isPill ? 'chatgpt-hotels' : 'chat__links'}>
      {isPill && <span className="chatgpt-hotels__label">Отели по вашему запросу</span>}
      <div className={isPill ? 'chatgpt-hotels__grid' : undefined}>
        {hotels.map((h) => (
          <Link
            key={h.slug}
            to={`/hotels/${h.slug}`}
            className={isPill ? 'chatgpt-hotel-pill' : 'chat__hotel-link'}
            onClick={() => onSelect?.(h.slug)}
          >
            <span className={isPill ? 'chatgpt-hotel-pill__name' : undefined}>{h.name}</span>
            <HotelStarsMark stars={h.stars} />
            {isPill && <span className="chatgpt-hotel-pill__arrow">→</span>}
          </Link>
        ))}
      </div>
    </div>
  );
}

/** Маленькая пометка «4★»; для отелей без категории ничего не показываем. */
export function HotelStarsMark({ stars }) {
  const n = Number(stars) || 0;
  if (n < 1) return null;
  return (
    <span className="chat-hotel-stars" title={`${n} из 5 звёзд`} aria-label={`${n} из 5 звёзд`}>
      {n}★
    </span>
  );
}
