import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

/**
 * Ответ нейронки в Markdown: эмодзи-заголовки, списки с «•», **жирный**,
 * в конце — сравнительная таблица (GFM). react-markdown не исполняет HTML,
 * поэтому ответ модели безопасен для вставки.
 */
export default function ChatMarkdown({ text }) {
  if (!text) return null;
  return (
    <div className="chat-md">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          // Ссылок в данных нет, но если модель что-то вставит — открываем в новой вкладке.
          a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />,
          // Таблица прокручивается по горизонтали на узких экранах, а не ломает колонку чата.
          table: ({ node, ...props }) => (
            <div className="chat-md__table-wrap"><table {...props} /></div>
          ),
        }}
      >
        {normalize(text)}
      </ReactMarkdown>
    </div>
  );
}

/** Модель размечает списки символом «•» — Markdown такого маркера не знает. */
function normalize(text) {
  return text.replace(/^(\s*)•\s?/gm, '$1- ');
}
