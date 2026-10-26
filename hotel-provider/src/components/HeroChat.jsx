import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { askAI, askSupport, loadHistory } from '../services/chatApi.js';

const CHANNELS = {
  ai: {
    label: 'ИИ-помощник',
    icon: '🤖',
    hello:
      'Здравствуйте! Я ваш персональный ИИ-гид по отелям России. Назовите город, даты или пожелания (у моря, спа, центр, бассейн, бюджет) — и я моментально подберу лучшие варианты.',
    send: askAI,
  },
  support: {
    label: 'Поддержка',
    icon: '💬',
    hello:
      'Вы в чате со службой заботы. Напишите ваш вопрос или опишите сложность — оператор ответит вам в ближайшее время.',
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

const initial = () =>
  Object.fromEntries(
    Object.entries(CHANNELS).map(([k, c]) => [k, [{ role: 'bot', text: c.hello }]])
  );

export default function HeroChat({ hotelSlug, onSelectHotel }) {
  const [channel, setChannel] = useState('ai');
  const [history, setHistory] = useState(initial);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const messagesBoxRef = useRef(null);
  const inputRef = useRef(null);

  const messages = history[channel];
  const streaming = messages[messages.length - 1]?.streaming;
  // Если в истории только первое приветствие — показываем красивый пустой экран в стиле ChatGPT/Claude
  const hasUserMessages = messages.some((m) => m.role === 'user');

  // Автоскролл только внутри контейнера сообщений
  useEffect(() => {
    if (messagesBoxRef.current && hasUserMessages) {
      messagesBoxRef.current.scrollTop = messagesBoxRef.current.scrollHeight;
    }
  }, [messages, pending, hasUserMessages]);

  // Загружаем сохранённую переписку с сервера при старте
  useEffect(() => {
    if (loaded) return;
    setLoaded(true);
    const keys = Object.keys(CHANNELS);
    Promise.all(keys.map((k) => loadHistory(k).catch(() => []))).then((res) =>
      setHistory((h) =>
        Object.fromEntries(
          keys.map((k, i) => [
            k,
            h[k].length === 1 && res[i].length ? [h[k][0], ...res[i]] : h[k],
          ])
        )
      )
    );
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

    const onToken = (t) =>
      update(ch, (arr) => {
        const last = arr[arr.length - 1];
        return last?.streaming
          ? [...arr.slice(0, -1), { ...last, text: last.text + t }]
          : [...arr, { role: 'bot', text: t, streaming: true }];
      });

    try {
      const reply = await CHANNELS[ch].send(next, { hotelSlug }, onToken);
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
      [channel]: [{ role: 'bot', text: CHANNELS[channel].hello }],
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
              <div className="chatgpt-typing-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 3. Плавающий инпут в стиле ChatGPT: выбор ИИ слева, строка по центру, поддержка справа */}
      <div className="chatgpt-input-dock">
        {/* Кнопка ИИ-помощник слева */}
        <button
          type="button"
          className={`chatgpt-channel-pill chatgpt-channel-pill--left ${
            channel === 'ai' ? 'is-active' : ''
          }`}
          onClick={(e) => {
            e.preventDefault();
            setChannel('ai');
          }}
          aria-selected={channel === 'ai'}
          title="Режим ИИ-помощника"
        >
          <span className="chatgpt-channel-pill__icon">🤖</span>
          <span className="chatgpt-channel-pill__label">ИИ-помощник</span>
          <span className="chatgpt-channel-pill__dot" />
        </button>

        {/* Центральное поле ввода */}
        <form className="chatgpt-bar" onSubmit={onSubmit}>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              channel === 'ai'
                ? 'Спросите о любом отеле, городе или пожеланиях...'
                : 'Напишите вопрос службе заботы...'
            }
            aria-label="Запрос к ИИ"
            disabled={pending}
          />
          <button
            type="submit"
            className="chatgpt-send-btn"
            disabled={!input.trim() || pending}
            aria-label="Отправить запрос"
            title="Отправить запрос"
          >
            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
              <path d="M12 4l-6 6h4v8h4v-8h4l-6-6z" />
            </svg>
          </button>
        </form>

        {/* Кнопка Поддержка справа */}
        <button
          type="button"
          className={`chatgpt-channel-pill chatgpt-channel-pill--right ${
            channel === 'support' ? 'is-active' : ''
          }`}
          onClick={(e) => {
            e.preventDefault();
            setChannel('support');
          }}
          aria-selected={channel === 'support'}
          title="Служба поддержки"
        >
          <span className="chatgpt-channel-pill__icon">💬</span>
          <span className="chatgpt-channel-pill__label">Поддержка</span>
        </button>
      </div>
    </div>
  );
}
