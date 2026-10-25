import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import Stars from '../components/Stars.jsx';
import Section from '../components/Section.jsx';
import { getHotelBySlug } from '../services/hotelsService.js';
import { ACCESS, formatPrice } from '../utils.js';
import NotFoundPage from './NotFoundPage.jsx';

export default function HotelPage() {
  const { slug } = useParams();
  const [hotel, setHotel] = useState(undefined); // undefined = грузится, null = не найден

  useEffect(() => {
    setHotel(undefined);
    getHotelBySlug(slug).then(setHotel);
  }, [slug]);

  if (hotel === undefined) return <div className="container"><p className="muted">Загрузка…</p></div>;
  if (hotel === null) return <NotFoundPage />;

  const h = hotel;
  const style = h.theme?.accent ? { '--accent': h.theme.accent } : undefined;
  const [mainImg, ...restImgs] = h.gallery.length ? h.gallery : [h.cover].filter(Boolean);

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
            <span>от</span> <strong>{formatPrice(h.priceFrom, h.currency)}</strong> <span>за ночь</span>
            <a href="#rooms" className="btn btn--orange">Выбрать номер</a>
          </div>
        </header>

        <div className="gallery">
          {mainImg ? <img className="gallery__main" src={mainImg} alt={h.name} /> : <div className="img-placeholder gallery__main">Главное фото</div>}
          {restImgs.slice(0, 4).map((src, i) => <img key={i} src={src} alt={`${h.name} — фото ${i + 2}`} loading="lazy" />)}
        </div>

        <div className="hotel-layout">
          <div className="hotel-layout__main">
            <Section id="about" title="Об отеле" show={h.description.length > 0}>
              {h.description.map((p, i) => <p key={i}>{p}</p>)}
            </Section>

            <Section id="amenities" title="Удобства" show={h.amenities.length > 0}>
              <ul className="chips">{h.amenities.map((a) => <li key={a}>{a}</li>)}</ul>
            </Section>

            <Section id="rooms" title="Номера" show={h.rooms.length > 0}>
              <div className="rooms">
                {h.rooms.map((r) => (
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

            <Section id="reviews" title="Отзывы" show={h.reviews.length > 0}>
              {h.reviews.map((r, i) => (
                <blockquote className="review" key={i}>
                  <div className="review__score">{r.rating}</div>
                  <div><p>{r.text}</p><footer className="muted">{r.author}{r.date && `, ${r.date}`}</footer></div>
                </blockquote>
              ))}
            </Section>

            <Section id="policies" title="Правила" show={h.policies.length > 0}>
              <dl className="policies">{h.policies.map((p) => (<div key={p.title}><dt>{p.title}</dt><dd>{p.text}</dd></div>))}</dl>
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
            {h.highlights.length > 0 && (
              <div className="panel"><h3>Коротко</h3>
                <dl className="facts">{h.highlights.map((x) => (<div key={x.label}><dt>{x.label}</dt><dd>{x.value}</dd></div>))}</dl>
              </div>
            )}
            {h.location && (
              <div className="panel"><h3>Расположение</h3>
                <p>{h.location.address}</p>
                {/* Сюда можно вставить карту (Leaflet/Google/Yandex) по h.location.lat / lng */}
                <div className="img-placeholder map">Карта</div>
                {h.location.nearby?.length > 0 && (
                  <ul className="nearby">{h.location.nearby.map((n) => (<li key={n.name}><span>{n.name}</span><span>{n.distance}</span></li>))}</ul>
                )}
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
