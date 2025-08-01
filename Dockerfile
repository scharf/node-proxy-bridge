# Build stage
FROM alpine:3.19 as builder

RUN apk add --no-cache python3 py3-pip gcc musl-dev python3-dev

WORKDIR /app
COPY requirements.txt .

# Install packages to a specific directory
RUN pip3 install --no-cache-dir --break-system-packages \
    --target=/app/packages \
    -r requirements.txt

# Runtime stage - fresh Alpine with no pip/setuptools
FROM alpine:3.19

RUN apk add --no-cache python3 && \
    rm -rf /usr/lib/python*/site-packages/*

WORKDIR /app

# Copy only the installed packages, not pip/setuptools
COPY --from=builder /app/packages /usr/lib/python3.11/site-packages/
COPY node_proxy_bridge.py .
COPY README.md .

# Create non-root user
RUN adduser -D -u 1000 appuser
USER appuser

ENV PYTHONPATH=/usr/lib/python3.11/site-packages

EXPOSE 8666

CMD ["python3", "-m", "uvicorn", "node_proxy_bridge:app", "--host", "0.0.0.0", "--port", "8666"]
