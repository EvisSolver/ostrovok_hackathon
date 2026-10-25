/** Блок страницы отеля. Не рендерится, если show=false (нет данных). */
export default function Section({ id, title, show = true, children }) {
  if (!show) return null;
  return (
    <section id={id} className="section">
      <h2>{title}</h2>
      {children}
    </section>
  );
}
