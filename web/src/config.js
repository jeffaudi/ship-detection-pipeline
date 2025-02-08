const defaultConfig = {
  development: {
    apiUrl: 'http://localhost:5454/api',
    wsUrl: 'ws://localhost:5454',
    coggerUrl: 'http://localhost:8181',
    titilerUrl: 'http://localhost:8282',
  },
  production: {
    apiUrl: 'https://ship-pipeline-api-577713910386.europe-west1.run.app/api',
    wsUrl: 'wss://ship-pipeline-api-577713910386.europe-west1.run.app',
    coggerUrl: 'https://ship-pipeline-cogger-577713910386.europe-west1.run.app',
    titilerUrl: 'https://ship-pipeline-titiler-577713910386.europe-west1.run.app',
  },
};

const env = process.env.VITE_ENV || 'development';
console.log('Current environment:', env);
console.log('Environment variables:', {
  VITE_ENV: process.env.VITE_ENV,
  VITE_API_URL: process.env.VITE_API_URL,
  VITE_WS_URL: process.env.VITE_WS_URL,
  VITE_COGGER_URL: process.env.VITE_COGGER_URL,
  VITE_TITILER_URL: process.env.VITE_TITILER_URL,
});

const config = {
  apiUrl: process.env.VITE_API_URL || defaultConfig[env].apiUrl,
  wsUrl: process.env.VITE_WS_URL || defaultConfig[env].wsUrl,
  coggerUrl: process.env.VITE_COGGER_URL || defaultConfig[env].coggerUrl,
  titilerUrl: process.env.VITE_TITILER_URL || defaultConfig[env].titilerUrl,
};

console.log('Final config:', config);

export default config;
