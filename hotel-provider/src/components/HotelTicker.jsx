import { useEffect, useMemo, useState } from 'react';
import HotelTickerCard from './HotelTickerCard.jsx';

export default function HotelTicker({
  hotels = [],
  direction = 'up', // 'up' | 'down'
  stepInterval = 3600, // Пауза перед прыжком
  delay = 0, // Смещение старта
  onSelectHotel,
  className = '',
}) {
  const [index, setIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  // Каждая карточка теперь крупнее (220px) + отступ (18px) = 238px.
  // За счёт этого в колонке видно значительно меньше отелей (всего 2-3 крупных карточки)
  const CARD_STEP = 238;
  const n = hotels.length;

  const repeatedHotels = useMemo(() => {
    if (!hotels.length) return [];
    return [...hotels, ...hotels, ...hotels];
  }, [hotels]);

  // Запуск периодического пружинистого прыжка
  useEffect(() => {
    if (isHovered || n === 0) return;

    let intervalId;
    const startTimeout = setTimeout(() => {
      intervalId = setInterval(() => {
        setIndex((prev) => prev + 1);
      }, stepInterval);
    }, delay);

    return () => {
      clearTimeout(startTimeout);
      if (intervalId) clearInterval(intervalId);
    };
  }, [isHovered, n, stepInterval, delay]);

  const handleTransitionEnd = () => {
    if (index >= n) {
      setIsTransitioning(false);
      setIndex(index % n);
    }
  };

  useEffect(() => {
    if (!isTransitioning) {
      const raf = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setIsTransitioning(true);
        });
      });
      return () => cancelAnimationFrame(raf);
    }
  }, [isTransitioning]);

  const offset =
    direction === 'up'
      ? -index * CARD_STEP
      : -(n * CARD_STEP) + index * CARD_STEP;

  return (
    <div
      className={`hotel-ticker hotel-ticker--bouncy ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      title="Наведите мышь, чтобы остановить"
    >
      <div
        className="hotel-ticker__track"
        style={{
          transform: `translateY(${offset}px)`,
          // Прыгающая пружинная кривая с овершутом (easeOutBack / spring overshoot)
          transition: isTransitioning
            ? 'transform 0.8s cubic-bezier(0.34, 1.56, 0.64, 1)'
            : 'none',
        }}
        onTransitionEnd={handleTransitionEnd}
      >
        {repeatedHotels.map((hotel, idx) => (
          <div key={`${hotel.id}-${idx}`} className="hotel-ticker__item">
            <HotelTickerCard hotel={hotel} onSelect={onSelectHotel} />
          </div>
        ))}
      </div>
    </div>
  );
}
