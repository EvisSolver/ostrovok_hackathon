import { Link } from 'react-router-dom';

export default function NotFoundPage() {
  return (
    <div className="container not-found">
      <h1>Страница не найдена</h1>
      <p>Проверьте адрес или вернитесь в каталог.</p>
      <Link to="/" className="btn">В каталог</Link>
    </div>
  );
}
