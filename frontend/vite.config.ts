import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

const host = process.env.VITE_DEV_HOST || 'localhost'
const isProduction = process.env.NODE_ENV === 'production'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    host: host,
    strictPort: false,
    hmr: isProduction ? false : {
      host: host === 'host.docker.internal' ? 'localhost' : host,
      port: 5173,
      protocol: 'ws',
      clientPort: 5173,
    },
    cors: {
      origin: '*',
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS'],
      credentials: true,
    },
    proxy: {
      '/api': {
        target: 'http://localhost:5000',
        changeOrigin: true,
        secure: false,
      },
      '/socket.io': {
        target: 'http://localhost:5000',
        ws: true,
        changeOrigin: true,
        secure: false,
      },
    },
    allowedHosts: ['localhost', 'host.docker.internal', '127.0.0.1'],
  },
  preview: {
    port: 4173,
    host: true,
    cors: true,
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          state: ['zustand'],
          ui: ['framer-motion', 'lucide-react', 'clsx'],
        },
      },
    },
  },
  optimizeDeps: {
    include: ['react', 'react-dom', 'zustand', 'socket.io-client'],
  },
})