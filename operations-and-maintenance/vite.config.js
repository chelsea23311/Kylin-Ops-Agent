import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/tasks': 'http://127.0.0.1:8000',
      '/api': 'http://127.0.0.1:8000',
      '/system': {
        target: 'http://127.0.0.1:8000',
        ws: true,
      },
      '/tools': 'http://127.0.0.1:8000',
      '/knowledge': 'http://127.0.0.1:8000',
      '/users': 'http://127.0.0.1:8000',
    },
  },
})
