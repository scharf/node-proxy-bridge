# node-proxy-bridge

Work around Node.js 20.12+ fetch() not respecting HTTP_PROXY environment variables.

Github: [scharf/node-proxy-bridge](https://github.com/scharf/node-proxy-bridge)<br>
Docker: [scharf/node-proxy-bridge](https://hub.docker.com/r/scharf/node-proxy-bridge)

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

## Design Philosophy: True Transparency

This proxy is designed to be **completely transparent**:

- **No timeouts**: The proxy imposes no time limits. Your application controls all timeouts.
- **No error modification**: HTTP errors pass through exactly as received from the upstream server.
- **No response tampering**: Headers, status codes, and bodies are preserved without modification.
- **No buffering delays**: Streaming responses flow through immediately.

### Why No Timeouts?

Many applications have long-running requests (file uploads, streaming responses, long computations). A proxy shouldn't make assumptions about appropriate timeouts - that's the client's decision. The proxy acts as a pure passthrough, letting your application handle timing as needed.

### Error Handling

- **HTTP errors (4xx, 5xx)**: Passed through unchanged with original status, headers, and body
- **Connection errors**: Return standard proxy status codes (502 Bad Gateway, 504 Gateway Timeout)
- **DNS failures**: Return 502 with the original error message (e.g., "Name does not resolve")

## Important: Designed for Internal Use Only

**This proxy is designed for internal usage within Docker Compose networks. It is not intended to be exposed publicly.**

HTTPS support and authentication are intentionally omitted due to the intended internal-only use case. The proxy is meant to be deployed within a controlled environment where network access is already restricted.

## Quick Start

```bash
docker run -d -p 8666:8666 \
  -e HTTPS_PROXY=http://corp-proxy:3128 \
  scharf/node-proxy-bridge:1.1.0
```

That's it! Now just prefix your URLs with `http://localhost:8666/`

### What You Get

✅ **Full transparency** - No timeouts, no modified errors, no altered responses  
✅ **Corporate proxy support** - Routes through your configured HTTP_PROXY  
✅ **Streaming support** - Real-time data flows through unchanged  
✅ **Simple integration** - Just change your base URL

## Docker Compose Example (Internal Network Only)

```yaml
version: '3.8'

services:
  node-proxy-bridge:
    image: scharf/node-proxy-bridge
    # No ports exposed to host - only accessible within internal network
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
    networks:
      - internal-net

  service1:
    image: your-service1
    environment:
      - API_BASE_URL=http://node-proxy-bridge:8666/api.example.com
    depends_on:
      - node-proxy-bridge
    networks:
      - internal-net

  service2:
    image: your-service2
    environment:
      - API_BASE_URL=http://node-proxy-bridge:8666/api.example.com
    depends_on:
      - node-proxy-bridge
    networks:
      - internal-net

networks:
  internal-net:
    internal: true  # This makes the network inaccessible from outside Docker
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

## Security & Limitations

### Internal Use Only
This proxy is designed exclusively for internal usage within Docker Compose networks or other controlled environments. It should never be exposed to the public internet or untrusted networks.

### Intentional Limitations
The following features are intentionally omitted due to the internal-only design:

- **No Authentication**: The proxy does not implement authentication mechanisms.
- **No HTTPS**: The proxy operates over HTTP only.
- **No Rate Limiting**: There are no built-in protections against excessive requests.

### SSL Verification
SSL verification is disabled by default to work with corporate proxies that do SSL inspection. For production use outside corporate networks:

```bash
docker run -d -p 8666:8666 -e PROXY_VERIFY_SSL=true scharf/node-proxy-bridge
```

### Best Practices
- Always use the internal network configuration shown in the Docker Compose example.
- Never expose the proxy port (8666) to external networks.
- Consider implementing network-level access controls if deploying in more complex environments.

## Related Issues

- [nodejs/help#4512](https://github.com/nodejs/help/issues/4512)
- [nodejs/node#8381](https://github.com/nodejs/node/issues/8381)
- [nodejs/undici#1650](https://github.com/nodejs/undici/issues/1650)

## License

MIT
