// vite.config.js
import { defineConfig } from 'vite';

export default defineConfig({
  base: '/',
  server: {
    port: 5173,
    open: true,
    // Proxy /api/* to the Vercel dev server during local development.
    // Run `vercel dev` (port 3000) alongside `npm run dev` to use serverless functions locally.
    proxy: {
      '/api': {
        target: 'http://localhost:3000',
        changeOrigin: true,
      },
    },
  },
});
