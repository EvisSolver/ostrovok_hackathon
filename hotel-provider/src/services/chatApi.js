/**
 * Связь фронта с сервером чатов (папка server/).
 *
 * POST /api/chat/stream — ИИ-помощник, ответ приходит потоком (Server-Sent Events):
 *     event: token  data: {"t": "кусок текста"}
 *     event: done   data: {"hotels": [{"slug": "...", "name": "..."}]}
 *     event: busy   data: {"retryAfter": 3}        // сервер перегружен, клиент повторит сам
 *     event: error  data: {"message": "..."}
 * POST /api/support — чат с поддержкой, обычный JSON-ответ {"reply": "..."}
 * GET  /api/history?channel=ai|support (заголовок X-User-Id) — {"messages": [{"role", "text"}]}
 *
 * Тело POST-запросов: { userId, channel: "ai" | "support", message, context: { path, hotelSlug } }
 * userId — постоянный id посетителя из localStorage (переживает перезапуск браузера).
 * Когда на сайте появятся аккаунты, достаточно подставить сюда id пользователя.
 */
const API = import.meta.env.VITE_API_URL ?? '/api';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

let memoryId = null; // запасной вариант, если localStorage недоступен
function newId() {
  return crypto.randomUUID?.() ?? `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 14)}`;
}

export function getUserId() {
  try {
    let id = localStorage.getItem('user-id');
    if (!id) { id = newId(); localStorage.setItem('user-id', id); }
    return id;
  } catch {
    return (memoryId ??= newId());
  }
}

function buildRequest(channel, messages, { hotelSlug } = {}) {
  const last = [...messages].reverse().find((m) => m.role === 'user');
  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: getUserId(),
      channel,
      message: last?.text ?? '',
      context: { path: window.location.pathname, hotelSlug: hotelSlug ?? null },
    }),
  };
}

async function readStream(body, onToken) {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buf = '', text = '', hotels = [];
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    let i;
    while ((i = buf.indexOf('\n\n')) >= 0) {
      const block = buf.slice(0, i);
      buf = buf.slice(i + 2);
      const event = /^event: (.*)$/m.exec(block)?.[1];
      const raw = /^data: (.*)$/m.exec(block)?.[1];
      const data = raw ? JSON.parse(raw) : {};
      if (event === 'token') { text += data.t; onToken?.(data.t); }
      else if (event === 'done') hotels = data.hotels ?? [];
      else if (event === 'busy') return { busy: data.retryAfter ?? 3 };
      else if (event === 'error') throw new Error(data.message || 'stream error');
    }
  }
  return { text, hotels };
}

/** ИИ: onToken вызывается на каждый кусок текста; при перегрузке запрос повторяется с паузой. */
export async function askAI(messages, ctx, onToken) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    const res = await fetch(`${API}/chat/stream`, buildRequest('ai', messages, ctx));
    if (res.status === 429 || res.status === 503) {
      await sleep((Number(res.headers.get('Retry-After')) || 3) * 1000 * attempt);
      continue;
    }
    if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
    const result = await readStream(res.body, onToken);
    if (result.busy) { await sleep(result.busy * 1000 * attempt); continue; }
    return result;
  }
  throw new Error('Сервер занят');
}

export async function askSupport(messages, ctx) {
  const res = await fetch(`${API}/support`, buildRequest('support', messages, ctx));
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  const data = await res.json();
  return { text: data.reply, hotels: [] };
}

/** Сохранённая переписка канала (для восстановления окна чата). */
export async function loadHistory(channel) {
  const res = await fetch(`${API}/history?channel=${channel}`, { headers: { 'X-User-Id': getUserId() } });
  if (!res.ok) return [];
  const { messages } = await res.json();
  return messages.map((m) => ({ role: m.role === 'user' ? 'user' : 'bot', text: m.text }));
}
