import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Stars from '../components/Stars.jsx';
import Section from '../components/Section.jsx';
import { getHotelBySlug } from '../services/hotelsService.js';
import { ACCESS, formatPrice } from '../utils.js';
import NotFoundPage from './NotFoundPage.jsx';
import HotelMap from '../components/HotelMap.jsx';

const NEARBY_LABELS = {
  park: 'Парк', water: 'Водоём', river: 'Река', road: 'Дорога',
  attraction: 'Достопримечательность', mall: 'Торговый центр', food: 'Кафе и места питания',
};

export default function HotelPage() {
  const { slug } = useParams();
  const [hotel, setHotel] = useState(undefined); // undefined = loading, null = not found
  const [loadError, setLoadError] = useState(false);

  useEffect(() => {
    let active = true;
    setHotel(undefined);
    setLoadError(false);
    getHotelBySlug(slug).then((result) => {
      if (active) setHotel(result);
    }).catch(() => {
      if (active) setLoadError(true);
    });
    return () => { active = false; };
  }, [slug]);

  if (hotel === undefined && loadError) return <div className="container"><p>Не удалось загрузить страницу отеля. Попробуйте обновить её.</p><Link to="/" className="back">← Все отели</Link></div>;
  if (hotel === undefined) return <div className="container"><p className="muted">Загрузка…</p></div>;
  if (hotel === null) return <NotFoundPage />;

  const h = hotel;
  const style = h.theme?.accent ? { '--accent': h.theme.accent } : undefined;
  const gallery = Array.isArray(h.gallery) ? h.gallery : [];
  const [mainImg, ...restImgs] = gallery.length ? gallery : [h.cover].filter(Boolean);

  return (
    <article className="hotel-page" style={style}>
      <div className="container">
        <Link to="/" className="back">← Все отели</Link>

        <header className="hotel-hero">
          <div>
            <div className="hotel-hero__meta"><Stars count={h.stars} />{h.rating && <span className="rating">{h.rating}</span>}</div>
            <h1>{h.name}</h1>
            {h.tagline && <p className="hotel-hero__tagline">{h.tagline}</p>}
            <p className="muted">{[h.location?.address, h.city, h.country].filter(Boolean).join(', ')}</p>
          </div>
          <div className="hotel-hero__price">
            {h.priceFrom != null ? (
              <>
                <span>от</span> <strong>{formatPrice(h.priceFrom, h.currency)}</strong>
                <span> {h.priceUnit === 'per_bed' ? 'за место / ночь' : 'за ночь'}</span>
                {h.priceIsMock && <small className="price-note">Ориентировочная mock-цена, не предложение бронирования</small>}
              </>
            ) : <span>Цена не указана</span>}
            <a href="#rooms" className="btn btn--orange">Выбрать номер</a>
          </div>
        </header>

        <div className="gallery">
          {mainImg ? <img className="gallery__main" src={mainImg} alt={h.name} /> : <div className="img-placeholder gallery__main">Главное фото</div>}
          {restImgs.slice(0, 4).map((src, i) => <img key={i} src={src} alt={`${h.name} — фото ${i + 2}`} loading="lazy" />)}
        </div>

        <div className="hotel-layout">
          <div className="hotel-layout__main">
            <Section id="about" title="Об отеле" show={Array.isArray(h.description) && h.description.length > 0}>
              {(Array.isArray(h.description) ? h.description : []).map((p, i) => <p key={i}>{p}</p>)}
            </Section>

            <Section id="amenities" title="Удобства" show={Array.isArray(h.amenities) && h.amenities.length > 0}>
              <ul className="chips">{(Array.isArray(h.amenities) ? h.amenities : []).map((a) => <li key={a}>{a}</li>)}</ul>
            </Section>

            <Section id="rooms" title="Номера" show={Array.isArray(h.rooms) && h.rooms.length > 0}>
              <div className="rooms">
                {(Array.isArray(h.rooms) ? h.rooms : []).map((r) => (
                  <div className="room" key={r.name}>
                    <div className="room__img">{r.image ? <img src={r.image} alt={r.name} loading="lazy" /> : <div className="img-placeholder">Фото</div>}</div>
                    <div className="room__info">
                      <h3>{r.name}</h3>
                      <p className="muted">{[r.size, r.guests && `до ${r.guests} гостей`, r.bed].filter(Boolean).join(' · ')}</p>
                    </div>
                    <div className="room__price"><strong>{formatPrice(r.price, h.currency)}</strong><span>за ночь</span></div>
                  </div>
                ))}
              </div>
            </Section>

            <Section id="reviews" title="Отзывы" show={Array.isArray(h.reviews) && h.reviews.length > 0}>
              {(Array.isArray(h.reviews) ? h.reviews : []).map((r, i) => (
                <blockquote className="review" key={i}>
                  <div className="review__score">{r.rating}</div>
                  <div><p>{r.text}</p><footer className="muted">{r.author}{r.date && `, ${r.date}`}</footer></div>
                </blockquote>
              ))}
            </Section>

            <Section id="policies" title="Правила" show={Array.isArray(h.policies) && h.policies.length > 0}>
              <dl className="policies">{(Array.isArray(h.policies) ? h.policies : []).map((p) => (<div key={p.title}><dt>{p.title}</dt><dd>{p.text}</dd></div>))}</dl>
            </Section>
          </div>

          <aside className="hotel-layout__side">
            {Object.keys(ACCESS).some((k) => h.access[k] != null) && (
              <div className="panel"><h3>Что рядом (пешком)</h3>
                <dl className="facts">{Object.entries(ACCESS).map(([k, a]) => h.access[k] != null && (
                  <div key={k}><dt>{a.short[0].toUpperCase() + a.short.slice(1)}</dt><dd>{h.access[k]} мин</dd></div>
                ))}</dl>
              </div>
            )}
            {Array.isArray(h.highlights) && h.highlights.length > 0 && (
              <div className="panel"><h3>Коротко</h3>
                <dl className="facts">{(Array.isArray(h.highlights) ? h.highlights : []).map((x) => (<div key={x.label}><dt>{x.label}</dt><dd>{x.value}</dd></div>))}</dl>
              </div>
            )}
            {h.location && (
              <div className="panel"><h3>Расположение</h3>
                {h.location.address && <p>{h.location.address}</p>}
                <HotelMap lat={h.location.lat ?? h.lat} lng={h.location.lng ?? h.lon} name={h.name} />
                {h.location.nearby?.length > 0 ? (
                  <>
                    <h4 className="nearby__heading">Что находится поблизости</h4>
                    <p className="nearby__note">Расстояния по прямой, рассчитанные по данным карты.</p>
                    <ul className="nearby">
                      {h.location.nearby.map((n, i) => (
                        <li key={`${i}-${n.category}-${n.name}`}>
                          <span className="nearby__name">
                            <span className="nearby__category">{NEARBY_LABELS[n.category] || 'Рядом'}</span>
                            {n.name}
                          </span>
                          <strong>{n.distance}</strong>
                        </li>
                      ))}
                    </ul>
                  </>
                ) : <p className="muted">Рядом не найдено именованных объектов из базы.</p>}
              </div>
            )}
            {h.contacts && (h.contacts.phone || h.contacts.email || h.contacts.website) && (
              <div className="panel"><h3>Контакты</h3>
                {h.contacts.phone && <p><a href={`tel:${h.contacts.phone}`}>{h.contacts.phone}</a></p>}
                {h.contacts.email && <p><a href={`mailto:${h.contacts.email}`}>{h.contacts.email}</a></p>}
                {h.contacts.website && <p><a href={h.contacts.website} target="_blank" rel="noreferrer">Сайт отеля</a></p>}
              </div>
            )}
          </aside>
        </div>
      </div>
    </article>
  );
}
