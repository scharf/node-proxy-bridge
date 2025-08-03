# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2025-08-03 - Transparent Proxy Enhancement

### Changed
- **Made proxy fully transparent**: Removed all custom error handling that wrapped errors
- **No timeouts by default**: Proxy now waits indefinitely, letting clients control their own timeouts
- **Improved error handling**:
  - HTTP errors (4xx, 5xx) pass through unchanged with original status, headers, and body
  - Connection errors return standard proxy status codes (502/504) with original error messages
  - No more custom error wrapping or modification
- **Simplified streaming errors**: Errors now just stop the stream naturally without injecting error messages
- **Cleaned up imports**: Removed unused TrustedHostMiddleware and other unnecessary imports

### Removed
- Global FastAPI exception handlers that wrapped errors in custom messages
- Default httpx timeouts that could interfere with long-running requests

### Why These Changes
The proxy is now truly transparent - it acts as a simple bridge that only adds corporate proxy routing without interfering with the actual HTTP communication. This design philosophy ensures:
- Clients have full control over timeouts
- Error messages are preserved exactly as received
- No unexpected behavior or modifications to responses
- Maximum compatibility with all types of HTTP traffic

## [1.0.1] - 2025-08-02 - Security and Performance Enhancement

### Added
- Explicit error handlers for proxy and general errors
- Enhanced connection pooling for better performance
- Improved logging and observability
- Security & Limitations documentation
- Internal-only network configuration example

### Changed
- Updated README.md with usage constraints and security recommendations
- Improved error handling with detailed error messages
- Enhanced HTTP connection pooling with optimized settings

## [1.0.1] - 2025-08-02 - Security update

### Changed
- Updated deployment script for better multi-platform support
- Improved Docker configuration
- Updated dependencies to latest versions:
  - fastapi==0.116.1
  - httpx==0.28.1
  - uvicorn==0.35.0

## [1.0.0] - 2025-08-01

### Added
- Initial release of node-proxy-bridge
- FastAPI-based proxy server to work around Node.js 20.12+ fetch() not respecting HTTP_PROXY environment variables
- Simple URL prefixing mechanism (http://localhost:8666/api.example.com)
- Support for all major HTTP methods (GET, POST, PUT, DELETE, PATCH)
- Streaming response support for LLM APIs and other streaming endpoints
- Option to disable streaming with the `proxy-no-streaming` path prefix
- Docker deployment support with provided Dockerfile
- Configurable SSL verification (disabled by default for corporate proxies)
- Detailed logging with configurable log levels
- Support for corporate proxies via HTTP_PROXY and HTTPS_PROXY environment variables
- Automatic Host header management
- Sensitive header redaction in logs
- Error handling with appropriate status codes
- Docker Hub deployment via deploy.sh script

### Security
- SSL verification is disabled by default to work with corporate proxies that do SSL inspection
- Option to enable SSL verification for production use outside corporate networks
- Support for custom CA bundles via PROXY_CA_BUNDLE environment variable
