FROM python:3.11-slim

# Metadata labels
LABEL org.opencontainers.image.source="https://github.com/scharf/node-proxy-bridge"
LABEL org.opencontainers.image.documentation="https://github.com/scharf/node-proxy-bridge#readme"
LABEL org.opencontainers.image.description="Work around Node.js 20.12+ fetch() not respecting HTTP_PROXY env vars"
LABEL org.opencontainers.image.licenses="MIT"

WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the application files
COPY node_proxy_bridge.py .
COPY README.md .

# Expose the proxy port
EXPOSE 8666

# Run the proxy server
CMD ["uvicorn", "node_proxy_bridge:app", "--host", "0.0.0.0", "--port", "8666"]
