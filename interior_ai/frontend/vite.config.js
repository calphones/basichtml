import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/upload': 'http://localhost:8000',
      '/design': 'http://localhost:8000',
      '/render': 'http://localhost:8000',
      '/edit': 'http://localhost:8000',
      '/assets': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
});
