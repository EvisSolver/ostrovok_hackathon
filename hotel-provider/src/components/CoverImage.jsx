import { useState } from 'react';

/**
 * Фото отеля с заглушкой. URL приходит из базы (hotels.photo_url, поле cover):
 * это внешние ссылки, поэтому если URL пуст или картинка не загрузилась —
 * показываем «Фото не найдено».
 */
export default function CoverImage({ src, alt, className, placeholderClassName = 'img-placeholder' }) {
  const [failedSrc, setFailedSrc] = useState(null);
  if (!src || failedSrc === src) {
    return <div className={placeholderClassName}>Фото не найдено</div>;
  }
  return <img className={className} src={src} alt={alt} loading="lazy" onError={() => setFailedSrc(src)} />;
}
