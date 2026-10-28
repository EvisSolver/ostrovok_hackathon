import { useEffect, useRef, useState } from 'react';
import ChatHotelLinks from './ChatHotelLinks.jsx';
import ChatMarkdown from './ChatMarkdown.jsx';
import { askAI, askSupport, loadHistory } from '../services/chatApi.js';

const CHANNELS = {
  ai: { label: 'Подбор отеля', send: askAI },
  support: { label: 'Поддержка', send: askSupport },
};

const PROMPT_SUGGESTIONS = [
  { title: 'Море и неспешные дни', subtitle: 'Сочи · отели у побережья', prompt: 'Подбери хороший отель в Сочи на первой линии у моря с бассейном' },
  { title: 'Большой город', subtitle: 'Москва · удобно добираться', prompt: 'Найди отель в центре Москвы рядом с метро до 10 000 рублей' },
  { title: 'Выходные с комфортом', subtitle: 'Спа, бассейн и завтраки', prompt: 'Посоветуй лучшие спа-отели 5 звёзд с завтраком и бассейном' },
  { title: 'Петербург по-своему', subtitle: 'Уютные места до 6 000 ₽', prompt: 'Какие есть недорогие отели в Санкт-Петербурге до 6000 рублей?' },
];

const initial = () => ({ ai: [], support: [] });

function getActiveFiltersList(filters, query) {
  const list = [];
  if (query?.trim()) list.push(`«${query.trim()}»`);
  if (filters?.city) list.push(filters.city);
  if (filters?.stars?.length) list.push(`${filters.stars.join(', ')}★`);
  if (filters?.maxPrice) list.push(`до ${filters.maxPrice.toLocaleString('ru-RU')} ₽`);
  if (filters?.sea) list.push(`море ≤${filters.sea}м`);
  if (filters?.metro) list.push(`метро ≤${filters.metro}м`);
  if (filters?.center) list.push(`центр ≤${filters.center}м`);
  return list;
}

export default function HeroChat({ hotelSlug, filters, query, onSelectHotel }) {
  const [channel, setChannel] = useState('ai');
  const [history, setHistory] = useState(initial);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const inputRef = useRef(null);

  const messages = history[channel];
  const streaming = messages[messages.length - 1]?.streaming;
  const hasUserMessages = messages.length > 0;
  const activeFilters = getActiveFiltersList(filters, query);

  useEffect(() => {
    if (loaded) return;
    setLoaded(true);
    const keys = Object.keys(CHANNELS);
    Promise.all(keys.map((k) => loadHistory(k).catch(() => []))).then((res) =>
      setHistory((h) => Object.fromEntries(keys.map((k, i) => [k, res[i] && res[i].length ? res[i] : []]))));
  }, [loaded]);

  const update = (ch, fn) => setHistory((h) => ({ ...h, [ch]: fn(h[ch]) }));

  async function handleSend(textToSend) {
    const text = (textToSend ?? input).trim();
    if (!text || pending) return;
    const ch = channel;
    const next = [...history[ch], { role: 'user', text }];
    update(ch, () => next);
    setInput('');
    setPending(true);

    const onToken = (t) => update(ch, (arr) => {
      const last = arr[arr.length - 1];
      return last?.streaming
        ? [...arr.slice(0, -1), { ...last, text: last.text + t }]
        : [...arr, { role: 'bot', text: t, streaming: true }];
    });

    try {
      const reply = await CHANNELS[ch].send(next, { hotelSlug, filters, query }, onToken);
      update(ch, (arr) => {
        const last = arr[arr.length - 1];
        return last?.streaming
          ? [...arr.slice(0, -1), { ...last, streaming: false, hotels: reply.hotels }]
          : [...arr, { role: 'bot', text: reply.text, hotels: reply.hotels }];
      });
    } catch {
      update(ch, (arr) => [...arr.map((m) => ({ ...m, streaming: false })), { role: 'bot', text: 'Не удалось получить ответ. Попробуйте ещё раз.', error: true }]);
    } finally {
      setPending(false);
    }
  }

  function resetChat() { setHistory((h) => ({ ...h, [channel]: [] })); }

  return (
    <div className="chatgpt-view">
      {!hasUserMessages ? (
        <div className="chatgpt-welcome">
          <h1 className="chatgpt-welcome__heading">Поездка начинается<br />с хорошего места.</h1>
          <p className="chatgpt-welcome__sub">Расскажите, куда собираетесь и что важно — подберём отель без лишних поисков.</p>
          <div className="chatgpt-prompts">
            {PROMPT_SUGGESTIONS.map((s) => (
              <button key={s.title} type="button" className="chatgpt-prompt-card" disabled={pending} onClick={() => handleSend(s.prompt)}>
                <span className="chatgpt-prompt-card__text">
                  <span className="chatgpt-prompt-card__title">{s.title}</span>
                  <span className="chatgpt-prompt-card__sub">{s.subtitle}</span>
                </span>
                <span className="chatgpt-prompt-card__arrow">→</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        <div className="chatgpt-stream" aria-live="polite">
          <div className="chatgpt-stream__header">
            <span className="chatgpt-stream__indicator"><span className="chatgpt-stream__dot" />{channel === 'ai' ? 'Подбор отеля' : 'Поддержка'}</span>
            <button type="button" className="chatgpt-stream__reset-btn" onClick={resetChat} title="Начать новый поиск">Новый поиск</button>
          </div>
          {messages.map((m, i) => (
            <div key={i} className={`chatgpt-msg chatgpt-msg--${m.role}${m.error ? ' is-error' : ''}`}>
              <span className="chatgpt-msg__avatar" data-role={m.role}>{m.role === 'bot' ? 'Помощник' : 'Вы'}</span>
              <div className="chatgpt-msg__body">
                <div className="chatgpt-msg__content">{m.role === 'bot' ? <ChatMarkdown text={m.text} /> : m.text}</div>
                <ChatHotelLinks hotels={m.hotels} onSelect={onSelectHotel} />
              </div>
            </div>
          ))}
          {pending && !streaming && <div className="chatgpt-msg chatgpt-msg--bot chatgpt-msg--typing">
            <span className="chatgpt-msg__avatar" data-role="bot">Помощник</span>
            <div className="chatgpt-typing-row"><span className="chatgpt-typing-row__text">Ищем подходящие варианты</span><div className="chatgpt-typing-dots"><span /><span /><span /></div></div>
          </div>}
        </div>
      )}

      <div className="chatgpt-filter-note">
        <span>Подбор учитывает фильтры каталога</span>
        {activeFilters.length > 0 && <span className="chatgpt-filter-note__tags" title="Активные фильтры">{activeFilters.join(' • ')}</span>}
      </div>

      <form className="chatgpt-input-dock" onSubmit={(e) => { e.preventDefault(); handleSend(); }}>
        <label className="chatgpt-bar">
          <span className="chatgpt-bar__label">ВАШИ ПОЖЕЛАНИЯ</span>
          <input ref={inputRef} value={input} onChange={(e) => setInput(e.target.value)} placeholder="Например, тихий отель у моря" aria-label="Пожелания к отелю" disabled={pending} />
        </label>
        <button type="submit" className={`chatgpt-submit-pill ${input.trim() && !pending ? 'is-ready' : ''}`} disabled={!input.trim() || pending} title="Подобрать подходящие отели" aria-label="Подобрать подходящие отели">
          <span>Подобрать</span>
          <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12h13M12 5l7 7-7 7" /></svg>
        </button>
      </form>
    </div>
  );
}
