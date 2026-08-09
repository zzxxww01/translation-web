import path from 'path';
// 从 vitest/config 导入：它是 vite defineConfig 的超集，多认一个 `test` 字段。
// 用 vite 的版本会让下面的 test 块过不了 tsc -b，进而卡死 npm run build。
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    // e2e 用 Playwright 单独跑（npx playwright test）。不排除的话 vitest 会
    // 收集 tests/e2e/*.spec.ts，在没装 @playwright/test 的环境里直接报错。
    exclude: ['**/node_modules/**', '**/dist/**', 'tests/e2e/**'],
  },
  server: {
    port: 8888,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/static': {
        target: 'http://localhost:8000',
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

          if (id.includes('@radix-ui')) {
            return 'radix-vendor';
          }

          if (
            id.includes('sonner') ||
            id.includes('class-variance-authority') ||
            id.includes('cmdk')
          ) {
            return 'ui-vendor';
          }

          if (
            id.includes('zustand') ||
            id.includes('clsx') ||
            id.includes('tailwind-merge')
          ) {
            return 'state-vendor';
          }
        },
      },
    },
  },
});
