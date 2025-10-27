import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://backend:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'http://backend:8000',
        ws: true,
        changeOrigin: true,
      },
      '/grafana': {  // Улучшен прокси для Grafana
        target: 'http://grafana:5050',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/grafana/, ''),
        configure: (proxy, _options) => {
          proxy.on('error', (err, _req, _res) => {
            console.log('Proxy error:', err);
          });
        },
      },
    },
  },
});