import { Outlet, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import ChatWidget from './ChatWidget.jsx';

export default function Layout() {
  const { pathname } = useLocation();
  const hotelSlug = pathname.startsWith('/hotels/') ? pathname.split('/')[2] : undefined;
  const isHome = pathname === '/';

  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);

  return (
    <div className="layout">
      <main className="layout__main"><Outlet /></main>

      <footer className="site-footer">
        <div className="container">© {new Date().getFullYear()} Отели. Все права защищены.</div>
      </footer>

      {/* На главной чат с ИИ встроен прямо в первый экран. На внутренних страницах (отели) показываем плавающий виджет */}
      {!isHome && <ChatWidget hotelSlug={hotelSlug} />}
    </div>
  );
}
