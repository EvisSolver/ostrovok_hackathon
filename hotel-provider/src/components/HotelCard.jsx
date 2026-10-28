import { Link } from 'react-router-dom';
import CoverImage from './CoverImage.jsx';
import Stars from './Stars.jsx';
import { ACCESS, formatPrice } from '../utils.js';

function hueFrom(str) {
  let h = 0;
  for (const c of str) h = (h * 31 + c.charCodeAt(0)) % 360;
  return h;
}

export default function HotelCard({ hotel, highlight }) {
  const { slug, name, city, region, stars, rating, reviewsCount, priceFrom, currency, cover, theme, access, tagline } = hotel;
  const place = [city, region !== city && region].filter(Boolean).join(', ');
  const style = { ...(theme?.accent ? { '--accent': theme.accent } : {}), '--hue': hueFrom(slug) };

  return (
    <Link to={`/hotels/${slug}`} className="hotel-card" style={style}>
      <div className="hotel-card__media">
        <CoverImage src={cover} alt={name} placeholderClassName="img-placeholder tinted" />
      </div>

      <div className="hotel-card__body">
        <div className="hotel-card__top">
          <Stars count={stars} />
          {rating && <span className="rating" title={`${reviewsCount} отзывов`}>{rating}</span>}
        </div>
        <h3>{name}</h3>
        <p className="hotel-card__place">{place}</p>
        {tagline && <p className="hotel-card__tagline">{tagline}</p>}
        <ul className="access">
          {Object.entries(ACCESS).map(([key, a]) =>
            access[key] != null ? (
              <li key={key} className={highlight === key ? 'is-hl' : ''}>
                <b>{access[key]} мин</b> {a.short}
              </li>
            ) : null
          )}
        </ul>
      </div>

      <div className="hotel-card__buy">
        <div className="hotel-card__price">{priceFrom != null ? (
          <><span>от</span><strong>{formatPrice(priceFrom, currency)}</strong><span>за ночь</span></>
        ) : <span>Цена не указана</span>}</div>
        <span className="btn btn--orange">Смотреть</span>
      </div>
    </Link>
  );
}
