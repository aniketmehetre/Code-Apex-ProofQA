import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5174,
    proxy: {
      '/sessions': 'http://127.0.0.1:8000',
      '/race': 'http://127.0.0.1:8000',
      '/verify': 'http://127.0.0.1:8000',
      '/certificates': 'http://127.0.0.1:8000',
      '/bench': 'http://127.0.0.1:8000',
      '/findings': 'http://127.0.0.1:8000'
    }
  }
});
