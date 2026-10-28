import { useEffect, useRef, useState } from 'react';
import ChatHotelLinks from './ChatHotelLinks.jsx';
import { askAI, askSupport, loadHistory } from '../services/chatApi.js';

const CHANNELS = {
  ai: { label: 'ИИ-помощник', hello: 'Здравствуйте! Помогу подобрать отель. Что ищете?', send: askAI },
  support: { label: 'Поддержка', hello: 'Вы в чате с поддержкой. Опишите вопрос — ответим как можно скорее.', send: askSupport },
};

const initial = () => Object.fromEntries(Object.keys(CHANNELS).map((k) => [k, []]));

export default function ChatWidget({ hotelSlug }) {
  const [open, setOpen] = useState(false);
  const [channel, setChannel] = useState('ai');
  const [history, setHistory] = useState(initial);
  const [input, setInput] = useState('');
  const [pending, setPending] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const messagesBoxRef = useRef(null);

  const messages = history[channel];
  const streaming = messages[messages.length - 1]?.streaming;

  useEffect(() => {
    if (messagesBoxRef.current) {
      messagesBoxRef.current.scrollTop = messagesBoxRef.current.scrollHeight;
    }
  }, [messages, open, pending]);

  // при первом открытии подтягиваем сохранённую переписку с сервера
  useEffect(() => {
    if (!open || loaded) return;
    setLoaded(true);
    const keys = Object.keys(CHANNELS);
    Promise.all(keys.map((k) => loadHistory(k).catch(() => []))).then((res) =>
      setHistory((h) => Object.fromEntries(keys.map((k, i) => [k, res[i] || []])))
    );
  }, [open, loaded]);

  const update = (ch, fn) => setHistory((h) => ({ ...h, [ch]: fn(h[ch]) }));

  async function onSubmit(e) {
    e.preventDefault();
    const text = input.trim();
    if (!text || pending) return;
    const ch = channel; // фиксируем канал, если пользователь переключится во время ответа
    const next = [...history[ch], { role: 'user', text }];
    update(ch, () => next);
    setInput('');
    setPending(true);

    // ответ ИИ приходит кусками: дописываем в последнее «стримящееся» сообщение
    const onToken = (t) => update(ch, (arr) => {
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

  return (
    <div className="chat">
      {open && (
        <div className="chat__panel" role="dialog" aria-label="Чат">
          <div className="chat__tabs" role="tablist">
            {Object.entries(CHANNELS).map(([key, c]) => (
              <button key={key} role="tab" aria-selected={channel === key} className={channel === key ? 'is-active' : ''} onClick={() => setChannel(key)}>
                {c.label}
              </button>
            ))}
            <button className="chat__close" onClick={() => setOpen(false)} aria-label="Закрыть чат">×</button>
          </div>

          <div ref={messagesBoxRef} className="chat__messages" aria-live="polite">
            {messages.length === 0 && (
              <div className="chat__msg chat__msg--bot chat__empty">
                {channel === 'ai'
                  ? 'Здравствуйте! Задайте вопрос по отелю или подбору номеров.'
                  : 'Здравствуйте! Опишите ваш вопрос — оператор поддержки на связи.'}
              </div>
            )}
            {messages.map((m, i) => (
              <div key={i} className={`chat__msg chat__msg--${m.role}${m.error ? ' is-error' : ''}`}>
                {m.text}
                <ChatHotelLinks hotels={m.hotels} variant="inline" />
              </div>
            ))}
            {pending && !streaming && <div className="chat__msg chat__msg--bot chat__typing">Печатает…</div>}
          </div>

          <form className="chat__form" onSubmit={onSubmit}>
            <input value={input} onChange={(e) => setInput(e.target.value)} placeholder="Напишите сообщение" aria-label="Сообщение" />
            <button type="submit" disabled={!input.trim() || pending}>Отправить</button>
          </form>
        </div>
      )}
      <button className="chat__toggle" onClick={() => setOpen((o) => !o)} aria-expanded={open}>
        {open ? 'Свернуть' : 'Чат'}
      </button>
    </div>
  );
}
