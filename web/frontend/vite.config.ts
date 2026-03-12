import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 8888,
    proxy: {
      '/api': {
        target: 'http://localhost:54321',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:54321',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (!id.includes('node_modules')) {
            return;
          }

          if (
            id.includes('react-router-dom') ||
            id.includes('react-dom') ||
            id.includes('/react/')
          ) {
            return 'react-vendor';
          }

          if (id.includes('@tanstack/react-query')) {
            return 'query-vendor';
          }

          if (id.includes('lucide-react')) {
            return 'icons-vendor';
          }

          if (
            id.includes('zustand') ||
            id.includes('clsx') ||
            id.includes('tailwind-merge')
          ) {
            return 'ui-vendor';
          }
        },
      },
    },
  },
});
