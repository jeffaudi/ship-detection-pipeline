import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ command, mode }) => {
  // Load env files based on mode
  const env = loadEnv(mode, process.cwd(), '')

  // Force production mode when VITE_ENV is set to production
  const isProduction = env.VITE_ENV === 'production'

  console.log('Vite config - Environment:', {
    mode,
    VITE_ENV: env.VITE_ENV,
    isProduction,
    VITE_API_URL: env.VITE_API_URL,
    VITE_WS_URL: env.VITE_WS_URL,
    VITE_API_KEY: env.VITE_API_KEY,
    VITE_COGGER_URL: env.VITE_COGGER_URL,
    VITE_TITILER_URL: env.VITE_TITILER_URL
  })

  return {
    plugins: [vue()],
    server: {
      port: 8080,
      host: true
    },
    define: {
      // Expose env variables
      __VUE_OPTIONS_API__: true,
      __VUE_PROD_DEVTOOLS__: false,
      // Force environment mode based on VITE_ENV
      'process.env.NODE_ENV': JSON.stringify(isProduction ? 'production' : 'development'),
      'process.env.VITE_ENV': JSON.stringify(env.VITE_ENV || 'development'),
      'process.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL),
      'process.env.VITE_WS_URL': JSON.stringify(env.VITE_WS_URL),
      'process.env.VITE_API_KEY': JSON.stringify(env.VITE_API_KEY),
      'process.env.VITE_COGGER_URL': JSON.stringify(env.VITE_COGGER_URL),
      'process.env.VITE_TITILER_URL': JSON.stringify(env.VITE_TITILER_URL)
    }
  }
})
