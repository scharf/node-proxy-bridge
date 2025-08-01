# node-proxy-bridge

Work around Node.js 20.12+ fetch() not respecting HTTP_PROXY environment variables.

## Why Another Proxy?

### The Problem

```javascript
// This used to work with HTTP_PROXY env var in Node.js < 20.12
await fetch('https://api.github.com/user');
// ❌ Error: fetch failed (doesn't respect HTTP_PROXY anymore)
```

Since Node.js 20.12+, the native fetch API doesn't respect `HTTP_PROXY`/`HTTPS_PROXY` environment variables. This breaks applications in corporate networks that require proxy servers.

### The Solution

```javascript
// Just prefix your URLs with the proxy address
await fetch('http://localhost:8666/api.github.com/user');
// ✅ Works! Routes through corporate proxy automatically
```

## Quick Start

```bash
docker run -d -p 8666:8666 \
  -e HTTPS_PROXY=http://corp-proxy:3128 \
  scharf/node-proxy-bridge
```

That's it! Now just prefix your URLs with `http://localhost:8666/`

## Docker Compose Example

```yaml
version: '3.8'

services:
  node-proxy-bridge:
    image: scharf/node-proxy-bridge
    ports:
      - "8666:8666"
    environment:
      # Required proxy settings for corporate networks
      - HTTPS_PROXY=http://corp-proxy:3128
      - HTTP_PROXY=http://corp-proxy:3128
      - NO_PROXY=localhost,127.0.0.1
      # Optional settings (uncomment as needed)
      # - PROXY_VERIFY_SSL=false  # Set to 'true' for production use outside corporate networks
      # - PROXY_CA_BUNDLE=/path/to/ca-bundle.crt  # Path to custom CA bundle if needed
      # - LOG_LEVEL=INFO  # Set to DEBUG for more verbose logging
    restart: unless-stopped

  your-app:
    image: your-app
    environment:
      - API_BASE_URL=http://node-proxy-bridge:8666/api.example.com
    depends_on:
      - node-proxy-bridge
```

### Using the proxy in your Node.js application

```javascript
// Example Node.js code using the proxy
const apiBaseUrl = process.env.API_BASE_URL || 'http://localhost:8666/api.example.com';

// Instead of this (which doesn't work in Node.js 20.12+):
// const response = await fetch('https://api.example.com/data');

// Do this (which works with the proxy):
const response = await fetch(`${apiBaseUrl}/data`);
const data = await response.json();
console.log(data);
```

## Usage

### Basic Usage
```
http://localhost:8666/api.openai.com/v1/chat/completions
```

### Disable Streaming
```
http://localhost:8666/proxy-no-streaming/api.example.com/endpoint
```

## Configuration

| Environment Variable | Description | Default |
|---------------------|-------------|---------|
| `HTTPS_PROXY` | Corporate proxy URL | - |
| `HTTP_PROXY` | Corporate proxy URL | - |
| `NO_PROXY` | Domains to bypass | - |
| `PROXY_VERIFY_SSL` | Enable SSL verification | `false` |
| `PROXY_CA_BUNDLE` | Path to CA bundle | - |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

## Security Note

SSL verification is disabled by default to work with corporate proxies that do SSL inspection. For production use outside corporate networks:

```bash
docker run -d -p 8666:8666 -e PROXY_VERIFY_SSL=true scharf/node-proxy-bridge
```

## Related Issues

- [nodejs/help#4512](https://github.com/nodejs/help/issues/4512)
- [nodejs/node#8381](https://github.com/nodejs/node/issues/8381)
- [nodejs/undici#1650](https://github.com/nodejs/undici/issues/1650)

## License

MIT
