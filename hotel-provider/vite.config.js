import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Запросы /api/* с фронта уходят на Python-сервер (папка server/), CORS настраивать не нужно.
export default defineConfig({
  plugins: [react()],
  server: { proxy: { '/api': 'http://localhost:8000' } },
});
