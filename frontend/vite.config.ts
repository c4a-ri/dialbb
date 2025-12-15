import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [vue()],
  base: './',
  build: {
    // outDir: '../static/new',
    outDir: '../dialbb/server/static/new',
    emptyOutDir: true
  }
})
