import { Link, NavLink, Outlet, useLocation } from 'react-router-dom';
import { useEffect } from 'react';
import ChatWidget from './ChatWidget.jsx';

export default function Layout() {
  const { pathname } = useLocation();
  const hotelSlug = pathname.startsWith('/hotels/') ? pathname.split('/')[2] : undefined;

  useEffect(() => { window.scrollTo(0, 0); }, [pathname]);

  return (
    <div className="layout">
      <header className="site-header">
        <div className="container site-header__inner">
          <Link to="/" className="logo">Отели<span>.</span></Link>
          <nav className="nav">
            <NavLink to="/" end>Каталог</NavLink>
            {/* добавьте новые страницы: <NavLink to="/about">О нас</NavLink> */}
          </nav>
        </div>
      </header>

      <main className="layout__main"><Outlet /></main>

      <footer className="site-footer">
        <div className="container">© {new Date().getFullYear()} Отели. Все права защищены.</div>
      </footer>

      <ChatWidget hotelSlug={hotelSlug} />
    </div>
  );
}
