import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    // `.pytest_cache` is an accidental pytest leftover in this workspace that
    // Windows can deny scandir on; never scan it (nor the backend temp dirs).
    exclude: ['**/node_modules/**', '**/dist/**', '**/coverage/**', '**/.git/**', '**/.pytest_cache/**', '**/.pytest_tmp/**'],
  },
})
