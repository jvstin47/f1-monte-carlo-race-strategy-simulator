import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/simulate': 'http://127.0.0.1:8005',
      '/compare': 'http://127.0.0.1:8005',
      '/undercut-analysis': 'http://127.0.0.1:8005',
      '/fastf1': 'http://127.0.0.1:8005',
      '/tracks': 'http://127.0.0.1:8005',
      '/optimize': 'http://127.0.0.1:8005',
      '/drivers': 'http://127.0.0.1:8005',
      '/optimize-mcts': 'http://127.0.0.1:8005',
      '/health': 'http://127.0.0.1:8005'
    }
  }
})
