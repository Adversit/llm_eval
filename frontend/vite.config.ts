import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// 自定义日志插件
const customLoggerPlugin = () => {
  return {
    name: 'custom-logger',
    configureServer(server: any) {
      server.middlewares.use((req: any, res: any, next: any) => {
        const timestamp = new Date().toLocaleTimeString('zh-CN', { hour12: false })
        console.log(`INFO: ${timestamp} - ${req.method} ${req.url}`)
        next()
      })
    },
    handleHotUpdate({ file }: any) {
      console.log(`INFO: File changed: ${file}`)
    },
  }
}

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), customLoggerPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  logLevel: 'info',
  clearScreen: false,
})
