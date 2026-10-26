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
      'Вы в чате со службой поддержки. Напишите ваш вопрос или опишите сложность — оператор ответит вам в ближайшее время.',
    send: askSupport,
  },
};

const SUGGESTIONS = [
  { icon: '🌊', text: 'Отель в Сочи у моря' },
  { icon: '🏛️', text: 'В центре Москвы рядом с метро' },
  { icon: '⭐', text: '5 звёзд со спа и завтраком' },
  { icon: '💰', text: 'Отель в СПб до 6 000 ₽' },
  { icon: '🏔️', text: 'Уютный отель в Красной Поляне' },
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

  // Автоскролл только внутри контейнера сообщений
  useEffect(() => {
    if (messagesBoxRef.current) {
      messagesBoxRef.current.scrollTop = messagesBoxRef.current.scrollHeight;
    }
  }, [messages, pending]);

  // Загружаем историю переписки с сервера при старте
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

  function handleChipClick(text) {
    setInput(text);
    handleSend(text);
  }

  function resetChat() {
    setHistory((h) => ({
      ...h,
      [channel]: [{ role: 'bot', text: CHANNELS[channel].hello }],
    }));
  }

  return (
    <div className="seamless-hero-chat">
      {/* 1. Блок сообщений чата: занимает всю высоту вверх, границы отсутствуют */}
      <div ref={messagesBoxRef} className="seamless-hero-chat__messages" aria-live="polite">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`seamless-hero-chat__msg seamless-hero-chat__msg--${m.role}${
              m.error ? ' is-error' : ''
            }`}
          >
            <div className="seamless-hero-chat__avatar">
              {m.role === 'bot' ? (channel === 'ai' ? '🤖' : '💬') : '👤'}
            </div>
            <div className="seamless-hero-chat__msg-content">
              <div className="seamless-hero-chat__bubble">{m.text}</div>
              {m.hotels?.length > 0 && (
                <div className="seamless-hero-chat__hotel-cards">
                  <span className="seamless-hero-chat__hotel-title">Рекомендуемые отели:</span>
                  <div className="seamless-hero-chat__hotel-list">
                    {m.hotels.map((h) => (
                      <Link
                        key={h.slug}
                        to={`/hotels/${h.slug}`}
                        className="seamless-hero-chat__hotel-link"
                        onClick={() => onSelectHotel?.(h.slug)}
                      >
                        <span className="seamless-hero-chat__hotel-icon">🏨</span>
                        <span className="seamless-hero-chat__hotel-name">{h.name}</span>
                        <span className="seamless-hero-chat__hotel-arrow">→</span>
                      </Link>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {pending && !streaming && (
          <div className="seamless-hero-chat__msg seamless-hero-chat__msg--bot seamless-hero-chat__typing">
            <div className="seamless-hero-chat__avatar">{channel === 'ai' ? '🤖' : '💬'}</div>
            <div className="seamless-hero-chat__bubble seamless-hero-chat__typing-bubble">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
      </div>

      {/* 2. Чипсы с быстрыми подсказками над инпутом */}
      <div className="seamless-hero-chat__suggestions">
        <span className="seamless-hero-chat__sugg-label">Попробуйте:</span>
        <div className="seamless-hero-chat__chips">
          {SUGGESTIONS.map((s, idx) => (
            <button
              key={idx}
              type="button"
              className="seamless-hero-chat__chip"
              disabled={pending}
              onClick={(e) => {
                e.preventDefault();
                handleChipClick(s.text);
              }}
            >
              <span>{s.icon}</span>
              <span>{s.text}</span>
            </button>
          ))}
        </div>
        <button
          type="button"
          className="seamless-hero-chat__reset-link"
          onClick={(e) => {
            e.preventDefault();
            resetChat();
          }}
          title="Сбросить историю диалога"
        >
          Очистить
        </button>
      </div>

      {/* 3. Нижний бар: переключатель ИИ слева, инпут по центру, поддержка справа */}
      <div className="seamless-hero-chat__dock">
        {/* СЛЕВА: ИИ-помощник */}
        <button
          type="button"
          className={`seamless-dock-btn seamless-dock-btn--left ${
            channel === 'ai' ? 'is-active' : ''
          }`}
          onClick={(e) => {
            e.preventDefault();
            setChannel('ai');
          }}
          aria-selected={channel === 'ai'}
          title="ИИ-помощник (онлайн)"
        >
          <span className="seamless-dock-btn__icon">🤖</span>
          <span className="seamless-dock-btn__label">ИИ-помощник</span>
          <span className="seamless-dock-btn__pulse" />
        </button>

        {/* ЦЕНТР: Поле ввода */}
        <form className="seamless-hero-chat__form" onSubmit={onSubmit}>
          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder={
              channel === 'ai'
                ? 'Спросите ИИ: «Подбери отель в Сочи с видом на море»...'
                : 'Напишите ваш вопрос в службу поддержки...'
            }
            aria-label="Сообщение"
            disabled={pending}
          />
          <button
            type="submit"
            className="seamless-hero-chat__submit-btn"
            disabled={!input.trim() || pending}
            aria-label="Отправить"
          >
            <span>Спросить</span>
            <svg
              viewBox="0 0 24 24"
              width="17"
              height="17"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.4"
              strokeLinecap="round"
              strokeLinejoin="round"
            >
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>

        {/* СПРАВА: Поддержка */}
        <button
          type="button"
          className={`seamless-dock-btn seamless-dock-btn--right ${
            channel === 'support' ? 'is-active' : ''
          }`}
          onClick={(e) => {
            e.preventDefault();
            setChannel('support');
          }}
          aria-selected={channel === 'support'}
          title="Чат с поддержкой"
        >
          <span className="seamless-dock-btn__icon">💬</span>
          <span className="seamless-dock-btn__label">Поддержка</span>
        </button>
      </div>
    </div>
  );
}
