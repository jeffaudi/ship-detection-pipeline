const config = {
  development: {
    apiUrl: 'http://localhost:5454/api',
    wsUrl: 'ws://localhost:5454',
    coggerUrl: 'http://localhost:8181',
    titilerUrl: 'http://localhost:8282',
  },
  production: {
    apiUrl: process.env.VITE_API_URL || 'https://api.example.com/api',
    wsUrl: process.env.VITE_WS_URL || 'wss://api.example.com',
    coggerUrl: process.env.VITE_COGGER_URL || 'https://cogger.example.com',
    titilerUrl: process.env.VITE_TITILER_URL || 'https://titiler.example.com',
  },
};

const env = process.env.NODE_ENV || 'development';
export default config[env];
