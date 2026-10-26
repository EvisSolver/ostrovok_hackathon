import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { askAI, askSupport, loadHistory } from '../services/chatApi.js';

const CHANNELS = {
  ai: {
    label: 'ИИ-помощник',
    icon: '🤖',
    send: askAI,
  },
  support: {
    label: 'Поддержка',
    icon: '💬',
    send: askSupport,
  },
};

const PROMPT_SUGGESTIONS = [
  {
    icon: '🌊',
    title: 'Отель в Сочи у моря',
    subtitle: 'Первая линия, бассейн и пляж',
    prompt: 'Подбери хороший отель в Сочи на первой линии у моря с бассейном',
  },
  {
    icon: '🏛️',
    title: 'Центр Москвы у метро',
    subtitle: '5 минут до метро и достопримечательностей',
    prompt: 'Найди отель в центре Москвы рядом с метро до 10 000 рублей',
  },
  {
    icon: '⭐',
    title: 'Премиум СПА и релакс',
    subtitle: '5 звёзд, термальный комплекс и завтраки',
    prompt: 'Посоветуй лучшие спа-отели 5 звёзд с завтраком и бассейном',
  },
  {
    icon: '💰',
    title: 'Доступный Петербург',
    subtitle: 'Уютные варианты до 6 000 ₽ за ночь',
    prompt: 'Какие есть недорогие отели в Санкт-Петербурге до 6000 рублей?',
  },
];

// Без стартовых сообщений по умолчанию: чат чистый с самого начала
const initial = () => ({
  ai: [],
  support: [],
});

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
  const messagesBoxRef = useRef(null);
  const inputRef = useRef(null);

  const messages = history[channel];
  const streaming = messages[messages.length - 1]?.streaming;
  const hasUserMessages = messages.length > 0;
  const activeFilters = getActiveFiltersList(filters, query);

  // Автоскролл только внутри контейнера сообщений
  useEffect(() => {
    if (messagesBoxRef.current && hasUserMessages) {
      messagesBoxRef.current.scrollTop = messagesBoxRef.current.scrollHeight;
    }
  }, [messages, pending, hasUserMessages]);

  // Загружаем сохранённую переписку с сервера при старте (если была)
  useEffect(() => {
    if (loaded) return;
    setLoaded(true);
    const keys = Object.keys(CHANNELS);
    Promise.all(keys.map((k) => loadHistory(k).catch(() => []))).then((res) =>
      setHistory((h) =>
        Object.fromEntries(keys.map((k, i) => [k, res[i] && res[i].length ? res[i] : []]))
      )
    );
  }, [loaded]);

  const update = (ch, fn) => setHistory((h) => ({ ...h, [ch]: fn(h[ch]) }));

  async function handleSend(textToSend) {
    const text = (textToSend ?? input).trim();
    if (!text || pending) return;

    const ch = channel;
    // Юзер видит только свой чистый введенный текст
    const next = [...history[ch], { role: 'user', text }];
    update(ch, () => next);
    setInput('');
    setPending(true);

    const onToken = (t) =>
      update(ch, (arr) => {
        const last = arr[arr.length - 1];
        return last?.streaming
          ? [...arr.slice(0, -1), { ...last, text: last.text + t }]
          : [...arr, { role: 'bot', text: t, streaming: true }];
      });

    try {
      // К запросу невидимо подмешиваются фильтры сайта
      const reply = await CHANNELS[ch].send(next, { hotelSlug, filters, query }, onToken);
      update(ch, (arr) => {
        const last = arr[arr.length - 1];
        return last?.streaming
          ? [...arr.slice(0, -1), { ...last, streaming: false, hotels: reply.hotels }]
          : [...arr, { role: 'bot', text: reply.text, hotels: reply.hotels }];
      });
    } catch {
      update(ch, (arr) => [
        ...arr.map((m) => ({ ...m, streaming: false })),
        { role: 'bot', text: 'Не удалось получить ответ. Попробуйте ещё раз.', error: true },
      ]);
    } finally {
      setPending(false);
    }
  }

  function onSubmit(e) {
    e.preventDefault();
    handleSend();
  }

  function resetChat() {
    setHistory((h) => ({
      ...h,
      [channel]: [],
    }));
  }

  return (
    <div className="chatgpt-view">
      {/* 1. Если диалог ещё не начат — экран в стиле ChatGPT / Claude */}
      {!hasUserMessages ? (
        <div className="chatgpt-welcome">
          <div className="chatgpt-welcome__badge">
            <span className="chatgpt-welcome__sparkle">✨</span>
            <span>ИИ-поиск и бронирование отелей</span>
          </div>
          <h1 className="chatgpt-welcome__heading">Куда вы хотите поехать?</h1>
          <p className="chatgpt-welcome__sub">
            Задайте вопрос нейросети или выберите готовую идею для отдыха
          </p>

          <div className="chatgpt-prompts">
            {PROMPT_SUGGESTIONS.map((s, idx) => (
              <button
                key={idx}
                type="button"
                className="chatgpt-prompt-card"
                disabled={pending}
                onClick={(e) => {
                  e.preventDefault();
                  handleSend(s.prompt);
                }}
              >
                <span className="chatgpt-prompt-card__icon">{s.icon}</span>
                <div className="chatgpt-prompt-card__text">
                  <span className="chatgpt-prompt-card__title">{s.title}</span>
                  <span className="chatgpt-prompt-card__sub">{s.subtitle}</span>
                </div>
                <span className="chatgpt-prompt-card__arrow">↑</span>
              </button>
            ))}
          </div>
        </div>
      ) : (
        /* 2. Если переписка идёт — сквозной поток сообщений на всю высоту */
        <div ref={messagesBoxRef} className="chatgpt-stream" aria-live="polite">
          <div className="chatgpt-stream__header">
            <span className="chatgpt-stream__indicator">
              <span className="chatgpt-stream__dot" />
              {channel === 'ai' ? 'ИИ-помощник активен' : 'Чат с поддержкой'}
            </span>
            <button
              type="button"
              className="chatgpt-stream__reset-btn"
              onClick={(e) => {
                e.preventDefault();
                resetChat();
              }}
              title="Начать новый диалог"
            >
              + Новый диалог
            </button>
          </div>

          {messages.map((m, i) => (
            <div
              key={i}
              className={`chatgpt-msg chatgpt-msg--${m.role}${m.error ? ' is-error' : ''}`}
            >
              <div className="chatgpt-msg__avatar">
                {m.role === 'bot' ? (channel === 'ai' ? '🤖' : '💬') : '👤'}
              </div>
              <div className="chatgpt-msg__body">
                <div className="chatgpt-msg__content">{m.text}</div>
                {m.hotels?.length > 0 && (
                  <div className="chatgpt-hotels">
                    <span className="chatgpt-hotels__label">Рекомендуемые варианты:</span>
                    <div className="chatgpt-hotels__grid">
                      {m.hotels.map((h) => (
                        <Link
                          key={h.slug}
                          to={`/hotels/${h.slug}`}
                          className="chatgpt-hotel-pill"
                          onClick={() => onSelectHotel?.(h.slug)}
                        >
                          <span className="chatgpt-hotel-pill__icon">🏨</span>
                          <span className="chatgpt-hotel-pill__name">{h.name}</span>
                          <span className="chatgpt-hotel-pill__arrow">→</span>
                        </Link>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))}

          {pending && !streaming && (
            <div className="chatgpt-msg chatgpt-msg--bot chatgpt-msg--typing">
              <div className="chatgpt-msg__avatar">{channel === 'ai' ? '🤖' : '💬'}</div>
              <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '0.9rem', color: '#64748b', fontWeight: 500 }}>
                  Нейросеть думает...
                </span>
                <div className="chatgpt-typing-dots">
                  <span></span>
                  <span></span>
                  <span></span>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. Пометка о том, что фильтры каталога учитываются ИИ */}
      <div className="chatgpt-filter-note">
        <span className="chatgpt-filter-note__icon">⚡</span>
        <span>Фильтры ниже также учитываются при ответе вам.</span>
        {activeFilters.length > 0 && (
          <span className="chatgpt-filter-note__tags" title="Активные фильтры">
            {activeFilters.join(' • ')}
          </span>
        )}
      </div>

      {/* 4. Плавающий инпут в стиле ChatGPT: надпись ИИ слева, строка по центру, кнопка «Отправить» справа */}
      <form className="chatgpt-input-dock" onSubmit={onSubmit}>
        {/* Слева: просто надпись «ИИ-помощник», без кнопки */}
        <div className="chatgpt-label-pill" title="ИИ-помощник активен">
          <span className="chatgpt-label-pill__icon">🤖</span>
          <span className="chatgpt-label-pill__text">ИИ-помощник</span>
          <span className="chatgpt-label-pill__dot" />
        </div>

        {/* По центру: поле ввода (отдельно от кнопки отправки) */}
        <div className="chatgpt-bar">
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Спросите о любом отеле, городе или пожеланиях..."
            aria-label="Запрос к ИИ"
            disabled={pending}
          />
        </div>

        {/* Справа: отдельная компактная кнопка «Отправить» вместо поддержки */}
        <button
          type="submit"
          className={`chatgpt-submit-pill ${input.trim() && !pending ? 'is-ready' : ''}`}
          disabled={!input.trim() || pending}
          title="Отправить запрос"
          aria-label="Отправить запрос"
        >
          <span>Отправить</span>
          <svg viewBox="0 0 24 24" width="15" height="15" fill="currentColor">
            <path d="M12 4l-6 6h4v8h4v-8h4l-6-6z" />
          </svg>
        </button>
      </form>
    </div>
  );
}
