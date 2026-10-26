import { useEffect, useMemo, useState } from 'react';
import HotelTickerCard from './HotelTickerCard.jsx';

export default function HotelTicker({
  hotels = [],
  direction = 'up', // 'up' | 'down'
  stepInterval = 3200, // Интервал между рывками в миллисекундах
  delay = 0, // Задержка перед первым рывком (для рассинхронизации колонок)
  onSelectHotel,
  className = '',
}) {
  const [index, setIndex] = useState(0);
  const [isTransitioning, setIsTransitioning] = useState(true);
  const [isHovered, setIsHovered] = useState(false);

  // Высота карточки (150px) + отступ снизу (14px) = 164px на один шаг
  const CARD_STEP = 164;
  const n = hotels.length;

  // Троекратное дублирование для плавного перехода в конце круга
  const repeatedHotels = useMemo(() => {
    if (!hotels.length) return [];
    return [...hotels, ...hotels, ...hotels];
  }, [hotels]);

  // Запуск периодического рывка
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

  // Когда дошли до конца одного полного набора отелей — незаметно сбрасываем без анимации
  const handleTransitionEnd = () => {
    if (index >= n) {
      setIsTransitioning(false);
      setIndex(index % n);
    }
  };

  useEffect(() => {
    if (!isTransitioning) {
      // Возвращаем плавный переход на следующем кадре браузера
      const raf = requestAnimationFrame(() => {
        requestAnimationFrame(() => {
          setIsTransitioning(true);
        });
      });
      return () => cancelAnimationFrame(raf);
    }
  }, [isTransitioning]);

  // Смещение в зависимости от направления: вверх или вниз
  const offset =
    direction === 'up'
      ? -index * CARD_STEP
      : -(n * CARD_STEP) + index * CARD_STEP;

  return (
    <div
      className={`hotel-ticker hotel-ticker--stepped ${className}`}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      title="Наведите курсор, чтобы приостановить движение"
    >
      <div
        className="hotel-ticker__track"
        style={{
          transform: `translateY(${offset}px)`,
          transition: isTransitioning
            ? 'transform 0.65s cubic-bezier(0.2, 1, 0.3, 1)'
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
