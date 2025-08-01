# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
