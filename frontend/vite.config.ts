import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const backendUrl = process.env.VITE_DEV_BACKEND_URL || 'http://localhost:8006';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3008,
    proxy: {
      '/api': backendUrl,
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'mantine-vendor': ['@mantine/core', '@mantine/hooks', '@mantine/notifications'],
          'pdf-vendor': ['react-pdf', 'pdfjs-dist'],
          'chart-vendor': ['recharts'],
          'data-vendor': ['@tanstack/react-query', 'zustand', 'axios'],
        },
      },
    },
    chunkSizeWarningLimit: 600,
  },
});
