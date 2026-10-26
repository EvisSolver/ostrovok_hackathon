import Stars from './Stars.jsx';
import { formatPrice } from '../utils.js';

export function HotelSceneGraphic({ scene = 'city', accent = '#1fa0f0' }) {
  if (scene === 'sea') {
    return (
      <svg viewBox="0 0 300 160" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`sea-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#ffeedd" />
            <stop offset="60%" stopColor="#fed7aa" />
            <stop offset="100%" stopColor="#7dd3fc" />
          </linearGradient>
          <linearGradient id={`sea-water-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#38bdf8" />
            <stop offset="100%" stopColor="#0369a1" />
          </linearGradient>
        </defs>
        <rect width="300" height="160" fill={`url(#sea-sky-${accent.slice(1)})`} />
        {/* Солнце */}
        <circle cx="210" cy="50" r="24" fill="#fbbf24" opacity="0.9" />
        {/* Море */}
        <rect y="95" width="300" height="65" fill={`url(#sea-water-${accent.slice(1)})`} />
        {/* Волны */}
        <path d="M0,105 Q75,98 150,105 T300,105 L300,160 L0,160 Z" fill="#0284c7" opacity="0.4" />
        <path d="M0,120 Q80,112 160,120 T300,120 L300,160 L0,160 Z" fill="#075985" opacity="0.3" />
        {/* Пальма */}
        <path d="M40,160 Q50,110 75,95 Q55,90 35,95 Q70,80 85,92 Q95,78 115,85 Q90,95 85,102 Q65,120 60,160 Z" fill="#064e3b" opacity="0.85" />
        {/* Отель на горизонте */}
        <rect x="180" y="70" width="70" height="30" rx="3" fill="#ffffff" opacity="0.85" />
        <rect x="190" y="65" width="50" height="10" rx="2" fill="#ffffff" opacity="0.8" />
      </svg>
    );
  }

  if (scene === 'mountain') {
    return (
      <svg viewBox="0 0 300 160" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`mnt-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e0f2fe" />
            <stop offset="70%" stopColor="#bae6fd" />
            <stop offset="100%" stopColor="#f8fafc" />
          </linearGradient>
          <linearGradient id={`mnt-grad-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#64748b" />
            <stop offset="100%" stopColor="#334155" />
          </linearGradient>
        </defs>
        <rect width="300" height="160" fill={`url(#mnt-sky-${accent.slice(1)})`} />
        {/* Горы задние */}
        <polygon points="60,130 140,40 220,130" fill="#94a3b8" opacity="0.6" />
        {/* Горы передние */}
        <polygon points="0,150 80,60 160,150" fill={`url(#mnt-grad-${accent.slice(1)})`} />
        <polygon points="120,150 200,50 290,150" fill={`url(#mnt-grad-${accent.slice(1)})`} />
        {/* Снег на вершине */}
        <polygon points="80,60 95,80 80,75 65,80" fill="#ffffff" />
        <polygon points="200,50 218,72 200,68 182,72" fill="#ffffff" />
        {/* Шале / Отель */}
        <polygon points="140,115 170,95 200,115" fill="#78350f" />
        <rect x="148" y="115" width="44" height="25" fill="#d97706" />
        <rect x="156" y="122" width="10" height="10" fill="#fef08a" />
        <rect x="174" y="122" width="10" height="10" fill="#fef08a" />
        {/* Ели */}
        <polygon points="30,150 45,120 60,150" fill="#14532d" />
        <polygon points="230,150 245,125 260,150" fill="#14532d" />
      </svg>
    );
  }

  if (scene === 'palace') {
    return (
      <svg viewBox="0 0 300 160" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`pal-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#faf5ff" />
            <stop offset="100%" stopColor="#ede9fe" />
          </linearGradient>
        </defs>
        <rect width="300" height="160" fill={`url(#pal-sky-${accent.slice(1)})`} />
        {/* Классический фасад */}
        <rect x="50" y="60" width="200" height="85" fill="#f8fafc" stroke="#cbd5e1" strokeWidth="2" />
        {/* Треугольный фронтон */}
        <polygon points="50,60 150,20 250,60" fill="#e2e8f0" stroke="#cbd5e1" strokeWidth="2" />
        <circle cx="150" cy="45" r="8" fill="#fbbf24" />
        {/* Колонны */}
        {[75, 105, 135, 165, 195, 225].map((x) => (
          <rect key={x} x={x} y="62" width="8" height="83" fill="#cbd5e1" rx="1" />
        ))}
        {/* Окна с арками */}
        {[88, 118, 178, 208].map((x) => (
          <rect key={x} x={x} y="85" width="14" height="26" rx="7" fill="#fef08a" opacity="0.9" />
        ))}
        {/* Дверь */}
        <rect x="140" y="105" width="20" height="40" rx="3" fill="#3b82f6" />
      </svg>
    );
  }

  if (scene === 'forest') {
    return (
      <svg viewBox="0 0 300 160" className="ticker-card__svg" preserveAspectRatio="none">
        <defs>
          <linearGradient id={`for-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#0f172a" />
            <stop offset="100%" stopColor="#1e3a5f" />
          </linearGradient>
        </defs>
        <rect width="300" height="160" fill={`url(#for-sky-${accent.slice(1)})`} />
        {/* Луна */}
        <circle cx="230" cy="40" r="14" fill="#fef08a" opacity="0.9" />
        {/* Звёзды */}
        {[40, 90, 150, 180, 270].map((x, i) => (
          <circle key={x} cx={x} cy={20 + (i % 3) * 12} r="1.5" fill="#ffffff" opacity="0.8" />
        ))}
        {/* Лесной склон */}
        <path d="M0,130 Q120,105 300,135 L300,160 L0,160 Z" fill="#064e3b" />
        {/* Деревья */}
        <polygon points="30,140 45,90 60,140" fill="#022c22" />
        <polygon points="65,145 80,100 95,145" fill="#044534" />
        <polygon points="210,145 225,95 240,145" fill="#022c22" />
        <polygon points="245,140 260,85 275,140" fill="#044534" />
        {/* Эко-домик A-frame */}
        <polygon points="125,145 155,90 185,145" fill="#78350f" />
        <polygon points="135,145 155,100 175,145" fill="#fef08a" opacity="0.9" />
      </svg>
    );
  }

  // city (default)
  return (
    <svg viewBox="0 0 300 160" className="ticker-card__svg" preserveAspectRatio="none">
      <defs>
        <linearGradient id={`city-sky-${accent.slice(1)}`} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor="#1e1b4b" />
          <stop offset="60%" stopColor="#312e81" />
          <stop offset="100%" stopColor="#4338ca" />
        </linearGradient>
      </defs>
      <rect width="300" height="160" fill={`url(#city-sky-${accent.slice(1)})`} />
      {/* Лучи заката */}
      <circle cx="150" cy="160" r="120" fill="#f59e0b" opacity="0.15" />
      {/* Небоскребы фон */}
      <rect x="20" y="60" width="35" height="90" fill="#1e1b4b" opacity="0.7" />
      <rect x="70" y="40" width="45" height="110" fill="#312e81" opacity="0.7" />
      <rect x="180" y="50" width="40" height="100" fill="#1e1b4b" opacity="0.7" />
      <rect x="235" y="30" width="50" height="120" fill="#312e81" opacity="0.7" />
      {/* Главный отель */}
      <rect x="115" y="25" width="70" height="125" rx="3" fill="#ffffff" opacity="0.92" />
      {/* Окна отеля с теплым светом */}
      {[35, 55, 75, 95, 115].map((y) => (
        <g key={y}>
          <rect x="125" y={y} width="12" height="10" rx="1" fill="#f59e0b" />
          <rect x="144" y={y} width="12" height="10" rx="1" fill="#38bdf8" />
          <rect x="163" y={y} width="12" height="10" rx="1" fill="#f59e0b" />
        </g>
      ))}
      <rect x="135" y="15" width="30" height="10" rx="2" fill="#e0e7ff" />
    </svg>
  );
}

export default function HotelTickerCard({ hotel, onSelect }) {
  const { name, city, stars, rating, priceFrom, tagline, badge, scene, accent } = hotel;

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
        {badge && <span className="ticker-card__badge-tag" style={{ backgroundColor: accent }}>{badge}</span>}
        <span className="ticker-card__rating">★ {rating}</span>
      </div>

      <div className="ticker-card__body">
        <div className="ticker-card__top">
          <Stars count={stars} />
          <span className="ticker-card__stars-text">{stars} звёзд</span>
        </div>
        <h4 className="ticker-card__name">{name}</h4>
        <p className="ticker-card__tagline">{tagline}</p>
        <div className="ticker-card__foot">
          <div className="ticker-card__price">
            <span>от</span> <strong>{formatPrice(priceFrom, 'RUB')}</strong> <span>/ ночь</span>
          </div>
          <span className="ticker-card__action">Выбрать →</span>
        </div>
      </div>
    </article>
  );
}
