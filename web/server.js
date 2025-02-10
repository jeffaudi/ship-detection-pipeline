import express from 'express';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';
import dotenv from 'dotenv';

// Load environment variables from .env (managed by Makefile)
dotenv.config();

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const app = express();
const PORT = process.env.PORT || 8080;

// Proxy middleware setup
const createProxyWithAuth = (target, pathRewrite = { '^/proxy': '' }) => {
  console.log(`Creating proxy for target: ${target}`);

  const targetUrl = new URL(target);

  return createProxyMiddleware({
    target,
    changeOrigin: true,
    pathRewrite: (path, req) => {
      console.log('Original path:', path);
      let newPath = path;
      // Apply each pathRewrite rule
      Object.entries(pathRewrite).forEach(([pattern, replacement]) => {
        newPath = newPath.replace(new RegExp(pattern), replacement);
      });
      console.log('Rewritten path:', newPath);
      return newPath;
    },
    // Increase timeouts for long-running requests (1 hour + buffer)
    timeout: 3660000,        // 1 hour + 1 minute in milliseconds
    proxyTimeout: 3660000,   // 1 hour + 1 minute in milliseconds
    // Increase buffer size for large responses
    maxBodyLength: 100 * 1024 * 1024,  // 100MB
    secure: true,
    // Keep connections alive
    keepAlive: true,
    keepAliveTimeout: 3660000,
    onProxyReq: (proxyReq, req) => {
      // Log the outgoing request (without sensitive data)
      console.log('Proxy request details:', {
        originalUrl: req.originalUrl,
        targetUrl: target + proxyReq.path,
        method: proxyReq.method,
        path: proxyReq.path
      });

      // Set headers directly on the proxy request
      proxyReq.setHeader('Host', targetUrl.host);
      proxyReq.setHeader('Origin', target);
      proxyReq.setHeader('X-API-Key', process.env.API_KEY || '');
      proxyReq.setHeader('Connection', 'keep-alive');

      // If it's a POST request, we need to handle the body
      if (req.method === 'POST' && req.body) {
        const bodyData = JSON.stringify(req.body);
        proxyReq.setHeader('Content-Type', 'application/json');
        proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
        proxyReq.write(bodyData);
      }
    },
    onError: (err, req, res) => {
      console.error('Proxy Error:', err);
      const errorMessage = {
        error: 'Proxy Error',
        message: err.message || 'Failed to connect to the target server',
        details: {
          target,
          path: req.path,
          originalUrl: req.originalUrl,
          method: req.method
        }
      };
      console.error('Error details:', errorMessage);
      res.writeHead(504, {
        'Content-Type': 'application/json',
      });
      res.end(JSON.stringify(errorMessage));
    },
    onProxyRes: (proxyRes, req, res) => {
      // Log the proxy response status
      console.log('Proxy response details:', {
        statusCode: proxyRes.statusCode,
        originalUrl: req.originalUrl,
        path: req.path,
        headers: {
          'content-type': proxyRes.headers['content-type'],
          'content-length': proxyRes.headers['content-length']
        }
      });

      // For image responses, ensure we don't modify the response
      if (proxyRes.headers['content-type']?.includes('image/')) {
        console.log('Handling image response');
        return;
      }

      // If we get a 403, log more details (without sensitive data)
      if (proxyRes.statusCode === 403) {
        console.log('Auth headers present:', {
          'X-API-Key': '****' + (process.env.API_KEY || '').slice(-4),
          'Host': proxyRes.req.getHeader('Host'),
          'Origin': proxyRes.req.getHeader('Origin')
        });
      }
    }
  });
};

// Add body parsing middleware for POST requests
app.use(express.json());

// Setup proxy routes
const setupProxy = () => {
  if (!process.env.VITE_API_URL) {
    console.error('VITE_API_URL is not set in environment');
    process.exit(1);
  }
  if (!process.env.VITE_COGGER_URL) {
    console.error('VITE_COGGER_URL is not set in environment');
    process.exit(1);
  }
  if (!process.env.VITE_TITILER_URL) {
    console.error('VITE_TITILER_URL is not set in environment');
    process.exit(1);
  }
  if (!process.env.API_KEY) {
    console.error('API_KEY is not set in environment');
    process.exit(1);
  }

  const apiUrl = process.env.VITE_API_URL.replace(/\/api\/?$/, '');
  console.log('Configured API URL:', {
    original: process.env.VITE_API_URL,
    modified: apiUrl
  });

  // For API routes
  app.use('/proxy/api', createProxyWithAuth(apiUrl, { '^/proxy/': '' }));
  app.use('/proxy/cogger', createProxyWithAuth(process.env.VITE_COGGER_URL, { '^/proxy/cogger/': '' }));
  app.use('/proxy/titiler', createProxyWithAuth(process.env.VITE_TITILER_URL, { '^/proxy/titiler/': '' }));
};

// Setup proxy first
setupProxy();

// Add error handling middleware
app.use((err, req, res, next) => {
  console.error('Server Error:', err);
  res.status(500).json({
    error: 'Server Error',
    message: err.message || 'An unexpected error occurred',
    details: {
      path: req.path,
      method: req.method
    }
  });
});

// Then serve static files
app.use(express.static(join(__dirname, 'dist')));

// Finally, handle SPA routing as the last resort
app.get('*', (req, res) => {
  res.sendFile(join(__dirname, 'dist', 'index.html'));
});

// Increase the server timeout
const server = app.listen(PORT, () => {
  server.timeout = 3660000; // 1 hour + 1 minute in milliseconds
  server.keepAliveTimeout = 3660000;
  server.headersTimeout = 3661000; // Should be greater than keepAliveTimeout

  console.log(`\nServer Configuration:`);
  console.log(`-------------------`);
  console.log(`Environment: ${process.env.VITE_ENV}`);
  console.log(`Port: ${PORT}`);
  console.log(`API URL: ${process.env.VITE_API_URL}`);
  console.log(`Cogger URL: ${process.env.VITE_COGGER_URL}`);
  console.log(`Titiler URL: ${process.env.VITE_TITILER_URL}`);
  console.log(`API Key: ${process.env.API_KEY ? '****' + process.env.API_KEY.slice(-4) : 'Not set'}`);
  console.log(`Timeout: ${server.timeout}ms`);
  console.log(`Keep-Alive Timeout: ${server.keepAliveTimeout}ms`);
  console.log(`Headers Timeout: ${server.headersTimeout}ms`);
  console.log(`-------------------\n`);
});
