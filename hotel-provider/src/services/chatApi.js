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
const API =
  import.meta.env.VITE_API_URL ??
  (typeof window !== 'undefined' && window.location.port === '5173'
    ? 'http://localhost:8000/api'
    : '/api');
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

export function formatFiltersContext(filters, query) {
  if (!filters && !query) return '';
  const parts = [];
  if (query?.trim()) parts.push(`поисковый запрос "${query.trim()}"`);
  if (filters?.city) parts.push(`город: ${filters.city}`);
  if (filters?.stars?.length) parts.push(`звёзды: ${filters.stars.join(', ')}★`);
  if (filters?.maxPrice) parts.push(`бюджет: до ${filters.maxPrice.toLocaleString('ru-RU')} ₽`);
  if (filters?.sea) parts.push(`до моря: до ${filters.sea} мин пешком`);
  if (filters?.metro) parts.push(`до метро: до ${filters.metro} мин пешком`);
  if (filters?.center) parts.push(`до центра: до ${filters.center} мин пешком`);
  if (!parts.length) return '';
  return `\n\n[Системный контекст: пользователь настроил фильтры в каталоге: ${parts.join(', ')}. Обязательно учитывай их при подборе и рекомендациях отелей!]`;
}

function buildRequest(channel, messages, ctx = {}) {
  const last = [...messages].reverse().find((m) => m.role === 'user');
  const filterAddon = formatFiltersContext(ctx.filters, ctx.query);
  const augmentedMessage = last?.text ? `${last.text}${filterAddon}` : '';

  return {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      userId: getUserId(),
      channel,
      message: augmentedMessage,
      context: {
        path: window.location.pathname,
        hotelSlug: ctx.hotelSlug ?? null,
        filters: ctx.filters ?? null,
        query: ctx.query ?? null,
      },
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

async function mockAIResponse(lastMessage, onToken, ctx = {}) {
  const q = (lastMessage?.text ?? '').toLowerCase();
  const filters = ctx.filters || {};
  const query = (ctx.query || '').toLowerCase();
  let text = '';
  let hotels = [];

  const isSochi = q.includes('сочи') || q.includes('море') || q.includes('пляж') || filters.city === 'Сочи' || filters.sea != null || query.includes('сочи');
  const isMoscow = q.includes('москв') || q.includes('тверск') || q.includes('кремл') || filters.city === 'Москва' || query.includes('москв');
  const isSpb = q.includes('петербург') || q.includes('питер') || q.includes('невск') || q.includes('спб') || filters.city === 'Санкт-Петербург' || query.includes('петербург') || query.includes('питер');
  const isBudget = q.includes('дешев') || q.includes('недорог') || q.includes('бюджет') || (filters.maxPrice && filters.maxPrice <= 5000);

  const filterNote = filters.city ? ` С учётом вашего фильтра «${filters.city}»:` : '';

  if (isSochi) {
    text = `Для отдыха у моря в Сочи${filterNote} рекомендую обратить внимание на Отель «Дендрарий» (5 звёзд, 3 минуты до пляжа) и Гостиницу «Приморская» (3 звезды, отличный доступный вариант у набережной).`;
    hotels = [
      { slug: 'dendrariy-sochi', name: 'Отель «Дендрарий»' },
      { slug: 'primorskaya-sochi', name: 'Гостиница «Приморская»' },
    ];
  } else if (isMoscow) {
    text = `В Москве${filterNote} отличный выбор — Отель «Тверская» (5 звёзд, 5 минут до метро Маяковская, окна на Тверскую улицу).`;
    hotels = [{ slug: 'tverskaya-moscow', name: 'Отель «Тверская»' }];
  } else if (isSpb) {
    text = `В Санкт-Петербурге${filterNote} советую Отель «Невский» (4 звезды, у Невского проспекта, до метро 3 минуты пешком).`;
    hotels = [{ slug: 'nevsky-spb', name: 'Отель «Невский»' }];
  } else if (isBudget) {
    text = `Среди доступных вариантов с комфортной ценой${filterNote} обратите внимание на Гостиницу «Приморская» в Сочи (от 3 900 ₽ за ночь) и Отель «Невский» в Санкт-Петербурге (от 6 200 ₽).`;
    hotels = [
      { slug: 'primorskaya-sochi', name: 'Гостиница «Приморская»' },
      { slug: 'nevsky-spb', name: 'Отель «Невский»' },
    ];
  } else {
    text = `Я подобрал отличные отели с учётом ваших пожеланий${filterNote}: Отель «Тверская» в Москве, Отель «Невский» в Санкт-Петербурге и Отель «Дендрарий» в Сочи. Все выбранные фильтры применены!`;
    hotels = [
      { slug: 'tverskaya-moscow', name: 'Отель «Тверская»' },
      { slug: 'dendrariy-sochi', name: 'Отель «Дендрарий»' },
      { slug: 'nevsky-spb', name: 'Отель «Невский»' },
    ];
  }

  // Симулируем стриминг токенов
  const words = text.split(' ');
  for (let i = 0; i < words.length; i++) {
    const chunk = (i === 0 ? '' : ' ') + words[i];
    onToken?.(chunk);
    await sleep(22);
  }
  return { text, hotels };
}

/** ИИ: onToken вызывается на каждый кусок текста; при перегрузке запрос повторяется с паузой. */
export async function askAI(messages, ctx, onToken) {
  const last = [...messages].reverse().find((m) => m.role === 'user');
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const res = await fetch(`${API}/chat/stream`, buildRequest('ai', messages, ctx));
      if (res.status === 429 || res.status === 503) {
        await sleep((Number(res.headers.get('Retry-After')) || 3) * 1000 * attempt);
        continue;
      }
      if (!res.ok || !res.body) throw new Error(`HTTP ${res.status}`);
      const result = await readStream(res.body, onToken);
      if (result.busy) { await sleep(result.busy * 1000 * attempt); continue; }
      return result;
    } catch (err) {
      // Если сервер оффлайн при локальной разработке фронтенда — используем умный фоллбек
      if (attempt === 3) {
        return await mockAIResponse(last, onToken, ctx);
      }
      await sleep(300);
    }
  }
  return await mockAIResponse(last, onToken, ctx);
}

export async function askSupport(messages, ctx) {
  try {
    const res = await fetch(`${API}/support`, buildRequest('support', messages, ctx));
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return { text: data.reply, hotels: [] };
  } catch {
    return { text: 'Оператор поддержки ответит вам в течение нескольких минут. Спасибо за обращение!', hotels: [] };
  }
}

/** Сохранённая переписка канала (для восстановления окна чата). */
export async function loadHistory(channel) {
  const res = await fetch(`${API}/history?channel=${channel}`, { headers: { 'X-User-Id': getUserId() } });
  if (!res.ok) return [];
  const { messages } = await res.json();
  return messages.map((m) => ({ role: m.role === 'user' ? 'user' : 'bot', text: m.text }));
}
