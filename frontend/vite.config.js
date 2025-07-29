import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig(({ command, mode }) => {
  return {
    plugins: [react()],
    server: command === 'serve' ? {
      proxy: {
        '/static/preprocessing': {
          target: 'http://localhost:8000',
          changeOrigin: true,
          rewrite: (path) => path,
        },
      },
    } : undefined, // No proxy in build mode
  };
});