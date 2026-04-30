import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    proxy: {
      '/auth': 'http://localhost:8000',
      '/collections': 'http://localhost:8000',
      '/photos': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    },
  },
})
