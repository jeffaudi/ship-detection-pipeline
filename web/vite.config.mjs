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

  // Validate required environment variables
  const apiUrl = env.VITE_API_URL?.replace(/\/api\/?$/, '');
  const coggerUrl = env.VITE_COGGER_URL;
  const titilerUrl = env.VITE_TITILER_URL;

  if (!apiUrl || !coggerUrl || !titilerUrl) {
    console.error('Missing required environment variables:', {
      VITE_API_URL: apiUrl || 'missing',
      VITE_COGGER_URL: coggerUrl || 'missing',
      VITE_TITILER_URL: titilerUrl || 'missing'
    });
    throw new Error('Missing required environment variables');
  }

  return {
    plugins: [vue()],
    server: {
      port: 8080,
      host: true,
      proxy: {
        '/proxy/api': {
          target: apiUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy/, ''),
          secure: true,
          headers: {
            'X-API-Key': process.env.API_KEY || ''
          }
        },
        '/proxy/cogger': {
          target: coggerUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy\/cogger/, ''),
          secure: true,
          headers: {
            'X-API-Key': process.env.API_KEY || ''
          }
        },
        '/proxy/titiler': {
          target: titilerUrl,
          changeOrigin: true,
          rewrite: (path) => path.replace(/^\/proxy\/titiler/, ''),
          secure: true,
          headers: {
            'X-API-Key': process.env.API_KEY || ''
          }
        }
      }
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
