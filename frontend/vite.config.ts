import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [uni()],
  server: {
    // 仅本地 H5 开发用：浏览器有 CORS 限制，需经 Vite 同源代理转发到 wiidu
    // 微信小程序不走这套代理，仍直连 https://www.wiidu.com.cn
    proxy: {
      '/zx': {
        target: 'https://www.wiidu.com.cn',
        changeOrigin: true,
        secure: true,
      },
      // backend Flask：python app.py → 8765
      '/seal-api': {
        target: 'http://127.0.0.1:8765',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/seal-api/, ''),
      },
    },
  },
})
