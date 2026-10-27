import Stars from './Stars.jsx';
import { formatPrice } from '../utils.js';

export function HotelSceneGraphic({ scene = 'city', accent = '#1fa0f0' }) {
  if (scene === 'sea') {
    return (
      <svg viewBox="0 0 320 180" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`sea-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ffedd5" />
            <stop offset="55%" stopColor="#fed7aa" />
            <stop offset="100%" stopColor="#bae6fd" />
          </linearGradient>
          <linearGradient id={`sea-water-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#0284c7" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#sea-sky-${accent.slice(1)})`} />
        {/* Солнце */}
        <circle cx="230" cy="55" r="28" fill="#fbbf24" opacity="0.9" />
        {/* Море */}
        <rect y="105" width="320" height="75" fill={`url(#sea-water-${accent.slice(1)})`} />
        {/* Волны */}
        <path d="M0,118 Q80,110 160,118 T320,118 L320,180 L0,180 Z" fill="#0284c7" opacity="0.45" />
        <path d="M0,135 Q90,126 180,135 T320,135 L320,180 L0,180 Z" fill="#0369a1" opacity="0.35" />
        {/* Пальмы на берегу */}
        <path d="M45,180 Q55,120 85,100 Q60,95 38,102 Q75,85 92,100 Q105,82 125,92 Q98,105 92,115 Q70,135 65,180 Z" fill="#064e3b" opacity="0.9" />
        {/* Силуэт отеля */}
        <rect x="195" y="78" width="80" height="35" rx="4" fill="#ffffff" opacity="0.92" />
        <rect x="208" y="70" width="54" height="10" rx="3" fill="#ffffff" opacity="0.85" />
      </svg>
    );
  }

  if (scene === 'mountain') {
    return (
      <svg viewBox="0 0 320 180" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`mnt-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e0f2fe" />
            <stop offset="70%" stopColor="#bae6fd" />
            <stop offset="100%" stopColor="#f1f5f9" />
          </linearGradient>
          <linearGradient id={`mnt-grad-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#64748b" />
            <stop offset="100%" stopColor="#334155" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#mnt-sky-${accent.slice(1)})`} />
        {/* Задние пики */}
        <polygon points="60,140 150,45 240,140" fill="#94a3b8" opacity="0.6" />
        {/* Передние горы */}
        <polygon points="0,170 90,65 180,170" fill={`url(#mnt-grad-${accent.slice(1)})`} />
        <polygon points="130,170 220,55 320,170" fill={`url(#mnt-grad-${accent.slice(1)})`} />
        {/* Снежные шапки */}
        <polygon points="90,65 108,90 90,82 72,90" fill="#ffffff" />
        <polygon points="220,55 240,80 220,74 200,80" fill="#ffffff" />
        {/* Шале */}
        <polygon points="150,130 185,108 220,130" fill="#78350f" />
        <rect x="160" y="130" width="50" height="28" fill="#d97706" />
        <rect x="168" y="138" width="12" height="12" rx="2" fill="#fef08a" />
        <rect x="188" y="138" width="12" height="12" rx="2" fill="#fef08a" />
        {/* Хвойные деревья */}
        <polygon points="35,170 50,135 65,170" fill="#14532d" />
        <polygon points="255,170 270,140 285,170" fill="#14532d" />
      </svg>
    );
  }

  if (scene === 'palace') {
    return (
      <svg viewBox="0 0 320 180" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`pal-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#faf5ff" />
            <stop offset="100%" stopColor="#ede9fe" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#pal-sky-${accent.slice(1)})`} />
        {/* Дворец */}
        <rect x="50" y="65" width="220" height="100" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
        <polygon points="50,65 160,22 270,65" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="2" />
        <circle cx="160" cy="48" r="9" fill="#fbbf24" />
        {[75, 110, 145, 175, 210, 245].map((x) => (
          <rect key={x} x={x} y="68" width="9" height="97" fill="#cbd5e1" rx="1" />
        ))}
        {[90, 125, 190, 225].map((x) => (
          <rect key={x} x={x} y="92" width="16" height="30" rx="8" fill="#fef08a" opacity="0.95" />
        ))}
        <rect x="150" y="115" width="22" height="50" rx="3" fill="#3b82f6" />
      </svg>
    );
  }

  if (scene === 'forest') {
    return (
      <svg viewBox="0 0 320 180" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`for-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f172a" />
            <stop offset="100%" stopColor="#1e3a5f" />
          </linearGradient>
        </defs>
        <rect width="320" height="180" fill={`url(#for-sky-${accent.slice(1)})`} />
        {/* Луна и звёзды */}
        <circle cx="250" cy="45" r="16" fill="#fef08a" opacity="0.9" />
        {[40, 95, 160, 200, 290].map((x, i) => (
          <circle key={x} cx={x} cy={22 + (i % 3) * 14} r="1.5" fill="#ffffff" opacity="0.8" />
        ))}
        <path d="M0,145 Q130,118 320,150 L320,180 L0,180 Z" fill="#064e3b" />
        <polygon points="30,160 45,100 60,160" fill="#022c22" />
        <polygon points="70,165 88,110 106,165" fill="#044534" />
        <polygon points="220,165 238,105 256,165" fill="#022c22" />
        {/* A-frame домик */}
        <polygon points="135,165 165,102 195,165" fill="#78350f" />
        <polygon points="145,165 165,115 185,165" fill="#fef08a" opacity="0.9" />
      </svg>
    );
  }

  // city (default)
  return (
    <svg viewBox="0 0 320 180" className="ticker-card__svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`city-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e1b4b" />
          <stop offset="60%" stopColor="#312e81" />
          <stop offset="100%" stopColor="#4338ca" />
        </linearGradient>
      </defs>
      <rect width="320" height="180" fill={`url(#city-sky-${accent.slice(1)})`} />
      <circle cx="160" cy="180" r="130" fill="#f59e0b" opacity="0.18" />
      <rect x="25" y="70" width="40" height="100" fill="#1e1b4b" opacity="0.75" />
      <rect x="80" y="45" width="50" height="125" fill="#312e81" opacity="0.75" />
      <rect x="195" y="55" width="45" height="115" fill="#1e1b4b" opacity="0.75" />
      <rect x="255" y="35" width="55" height="135" fill="#312e81" opacity="0.75" />
      <rect x="125" y="25" width="75" height="145" rx="4" fill="#ffffff" opacity="0.94" />
      {[38, 60, 82, 104, 126].map((y) => (
        <g key={y}>
          <rect x="135" y={y} width="13" height="11" rx="2" fill="#f59e0b" />
          <rect x="156" y={y} width="13" height="11" rx="2" fill="#38bdf8" />
          <rect x="177" y={y} width="13" height="11" rx="2" fill="#f59e0b" />
        </g>
      ))}
      <rect x="145" y="14" width="35" height="11" rx="2" fill="#e0e7ff" />
    </svg>
  );
}

export default function HotelTickerCard({ hotel, onSelect }) {
  const { name, city, stars, rating, priceFrom, tagline, scene, accent } = hotel;

  return (
    <article
      className="ticker-card"
      onClick={() => onSelect?.(hotel)}
      role="button"
      tabIndex={0}
      title={`${name} — ${city}`}
    >
      <div className="ticker-card__media">
        <HotelSceneGraphic scene={scene} accent={accent} />
        <span className="ticker-card__badge-city">{city}</span>
        <span className="ticker-card__rating">★ {rating}</span>
      </div>

      <div className="ticker-card__body">
        <div>
          <div className="ticker-card__top">
            <Stars count={stars} />
            <span className="ticker-card__stars-text">{stars} звёзд</span>
          </div>
          <h4 className="ticker-card__name">{name}</h4>
          <p className="ticker-card__tagline">{tagline}</p>
        </div>

        <div className="ticker-card__foot">
          <div className="ticker-card__price">
            <span>от</span> <strong>{formatPrice(priceFrom, 'RUB')}</strong> <span>/ ночь</span>
          </div>
          <span className="ticker-card__action">Смотреть →</span>
        </div>
      </div>
    </article>
  );
}
