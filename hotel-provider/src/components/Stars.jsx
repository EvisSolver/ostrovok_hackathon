export default function Stars({ count = 0 }) {
  return (
    <span className="stars" role="img" aria-label={`${count} из 5 звёзд`}>
      {Array.from({ length: 5 }, (_, i) => (
        <svg key={i} viewBox="0 0 20 20" className={i < count ? 'is-on' : ''} aria-hidden="true">
          <path d="M10 1.5l2.7 5.6 6.1.8-4.5 4.2 1.1 6.1L10 15.3l-5.4 2.9 1.1-6.1L1.2 7.9l6.1-.8z" />
        </svg>
      ))}
    </span>
  );
}
