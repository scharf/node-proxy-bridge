import asyncio
import httpx
import json
import logging
import os
from fastapi import FastAPI, Request, Response
from fastapi.responses import StreamingResponse
from httpx import StreamClosed, ConnectError, TimeoutException
from urllib.parse import urlparse

# Set up logging
log_level = os.environ.get("LOG_LEVEL", "INFO").upper()
numeric_level = getattr(logging, log_level, logging.INFO)

logging.basicConfig(
    level=numeric_level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Log to stdout only
logger.info(f"Proxy server starting with log level: {log_level}")
logger.info(f"Logging to stdout only")

# SSL Configuration (declare early for client initialization)
verify_ssl = os.environ.get("PROXY_VERIFY_SSL", "false").lower() == "true"
ca_bundle = os.environ.get("PROXY_CA_BUNDLE", None)

if ca_bundle:
    ssl_verify = ca_bundle
elif verify_ssl:
    ssl_verify = True
else:
    ssl_verify = False

# Print startup documentation from README.md
try:
    with open("/app/README.md", "r") as f:
        readme_content = f.read()

    logger.info("=" * 80)
    for line in readme_content.split("\n"):
        logger.info(line)
    logger.info("=" * 80)
    logger.info("")

except FileNotFoundError:
    logger.info("node-proxy-bridge - Bridge Node.js 20.12+ with corporate proxies")
    logger.info("See README.md for full documentation")
    logger.info("")

# Log proxy configuration at startup
logger.info("CORPORATE PROXY CONFIGURATION:")
if os.getenv("HTTPS_PROXY"):
    logger.info(f"  HTTPS_PROXY: {os.getenv('HTTPS_PROXY')}")
if os.getenv("HTTP_PROXY"):
    logger.info(f"  HTTP_PROXY: {os.getenv('HTTP_PROXY')}")
if os.getenv("NO_PROXY"):
    logger.info(f"  NO_PROXY: {os.getenv('NO_PROXY')}")
if not any([os.getenv("HTTPS_PROXY"), os.getenv("HTTP_PROXY")]):
    logger.info("  No corporate proxy configured - direct connections")
logger.info("")

# SSL Configuration
if ca_bundle:
    logger.info(f"SSL VERIFICATION: Enabled with CA bundle: {ca_bundle}")
elif verify_ssl:
    logger.info("SSL VERIFICATION: Enabled")
else:
    logger.warning("SSL VERIFICATION: Disabled - only use in trusted environments")

logger.info("")
logger.info("=" * 80)

app = FastAPI(
    title="Node Proxy Bridge",
    description="A proxy server to work around Node.js 20.12+ fetch() not respecting HTTP_PROXY environment variables",
)

# Note: FastAPI uses Starlette which has no built-in request size limit
# ASGI servers (uvicorn) may have their own limits that need to be configured
# at the server level, not here


# Parse proxy options from path
def parse_proxy_path(path: str):
    """Parse path like /proxy-large-timeout/api.example.com/endpoint
    Returns: (proxy_options, target_url)
    """
    logger.debug(f"Parsing proxy path: {path}")

    if not path.startswith("/"):
        path = "/" + path
        logger.debug(f"Added leading slash to path: {path}")

    # Remove leading slash and split
    parts = path[1:].split("/")
    if not parts:
        logger.debug("Path has no parts after splitting")
        return [], None

    # Find first part with dots (domain)
    domain_index = None
    for i, part in enumerate(parts):
        if "." in part and not part.startswith("proxy-"):
            domain_index = i
            logger.debug(f"Found domain part at index {i}: {part}")
            break

    if domain_index is None:
        logger.debug("No domain part found in path")
        return [], None

    # Extract proxy options (everything before domain)
    proxy_options = parts[:domain_index]

    # Build target URL (domain + path)
    domain_and_path = "/".join(parts[domain_index:])
    target_url = f"https://{domain_and_path}"

    logger.debug(f"Parsed proxy path: options={proxy_options}, target_url={target_url}")
    return proxy_options, target_url


def should_stream_from_options(proxy_options: list, body_json: dict) -> bool:
    """Determine if response should be streamed"""
    if "proxy-no-streaming" in proxy_options:
        logger.debug("Streaming disabled due to proxy-no-streaming option")
        return False

    # Default streaming detection for LLMs
    stream_from_body = body_json.get("stream", False) if body_json else False
    if stream_from_body:
        logger.debug("Streaming enabled based on 'stream: true' in request body")
    else:
        logger.debug("Streaming not requested in body or body not available")

    return stream_from_body


# Default client with no timeouts
client = httpx.AsyncClient(
    trust_env=True,  # uses HTTPS_PROXY from env
    verify=ssl_verify,  # Configurable SSL verification
    follow_redirects=True,
    limits=httpx.Limits(max_keepalive_connections=50, max_connections=100),
    timeout=httpx.Timeout(
        connect=None, read=None, write=None, pool=None  # No timeout by default
    ),
)


def redact_sensitive_headers(headers: dict) -> dict:
    """Redact sensitive information from headers for logging"""
    redacted_headers = headers.copy()
    sensitive_headers = ["authorization", "cookie", "x-api-key", "api-key"]

    for header in sensitive_headers:
        if header in redacted_headers:
            redacted_headers[header] = "[REDACTED]"

    return redacted_headers


@app.api_route("/{full_path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy(full_path: str, request: Request):
    start_time = asyncio.get_event_loop().time()
    request_id = f"{request.method}-{int(start_time * 1000)}"

    logger.info(f"[{request_id}] Received request: {request.method} {request.url.path}")
    logger.debug(f"[{request_id}] Request query params: {request.url.query}")

    # Log headers (redacted)
    redacted_req_headers = redact_sensitive_headers(dict(request.headers))
    logger.debug(f"[{request_id}] Request headers: {redacted_req_headers}")

    # Get the path
    path = request.url.path

    # Parse the proxy path
    proxy_options, target_url = parse_proxy_path(path)

    if not target_url:
        logger.warning(f"[{request_id}] Unknown route: {request.url.path}")
        return Response("Unknown route - path must contain a domain", status_code=404)

    # Add query parameters if present
    if request.url.query:
        target_url += f"?{request.url.query}"

    logger.info(
        f"[{request_id}] Proxy request: {request.method} {request.url.path} -> {target_url}"
    )

    # Copy headers
    headers = dict(request.headers)
    headers.pop("host", None)

    # Extract domain from target_url for Host header
    parsed_url = urlparse(target_url)
    headers["host"] = parsed_url.netloc
    logger.debug(f"[{request_id}] Setting Host header to: {parsed_url.netloc}")

    try:
        req_body = await request.body()

        # Log with body size info
        body_size = len(req_body) if req_body else 0
        logger.info(
            f"[{request_id}] Proxying {request.method} {target_url} (body: {body_size:,} bytes)"
        )

        # Check if this is a streaming request
        body_json = None
        if req_body:
            try:
                body_json = json.loads(req_body.decode("utf-8"))
                logger.debug(f"[{request_id}] Request body type: JSON")
            except (json.JSONDecodeError, UnicodeDecodeError):
                logger.debug(f"[{request_id}] Request body type: Binary/non-JSON")
                pass

        is_streaming_request = should_stream_from_options(proxy_options, body_json)
        logger.info(
            f"[{request_id}] Proxy options: {proxy_options}, Streaming: {is_streaming_request}"
        )

        # If it's a streaming request, use streaming response
        if is_streaming_request:
            logger.debug(f"[{request_id}] Setting up streaming response")

            async def stream_response():
                chunks_count = 0
                total_bytes = 0
                stream_start_time = asyncio.get_event_loop().time()

                try:
                    logger.debug(
                        f"[{request_id}] Starting streaming request to {target_url}"
                    )
                    async with client.stream(
                        method=request.method,
                        url=target_url,
                        headers=headers,
                        content=req_body,
                    ) as resp:
                        logger.info(
                            f"[{request_id}] Stream started, status: {resp.status_code}"
                        )
                        logger.debug(
                            f"[{request_id}] Response headers: {dict(resp.headers)}"
                        )

                        # Send headers info if needed
                        async for chunk in resp.aiter_raw():
                            if chunk:
                                chunks_count += 1
                                total_bytes += len(chunk)
                                if (
                                    chunks_count % 100 == 0
                                ):  # Log every 100 chunks to avoid excessive logging
                                    logger.debug(
                                        f"[{request_id}] Streamed {chunks_count} chunks, {total_bytes} bytes so far"
                                    )
                                yield chunk

                    stream_duration = (
                        asyncio.get_event_loop().time() - stream_start_time
                    )
                    logger.info(
                        f"[{request_id}] Stream completed: {chunks_count} chunks, {total_bytes} bytes in {stream_duration:.2f}s"
                    )

                except StreamClosed:
                    stream_duration = (
                        asyncio.get_event_loop().time() - stream_start_time
                    )
                    logger.warning(
                        f"[{request_id}] Stream closed by upstream after {stream_duration:.2f}s"
                    )
                    # Just stop streaming naturally
                    return

                except httpx.HTTPStatusError as e:
                    stream_duration = (
                        asyncio.get_event_loop().time() - stream_start_time
                    )
                    logger.error(
                        f"[{request_id}] HTTP status error in stream after {stream_duration:.2f}s: {str(e)}",
                        exc_info=True,
                    )
                    # For streaming, we can't return a proper error response
                    # Just stop the stream
                    return

                except httpx.RequestError as e:
                    stream_duration = (
                        asyncio.get_event_loop().time() - stream_start_time
                    )
                    logger.error(
                        f"[{request_id}] Request error in stream after {stream_duration:.2f}s: {str(e)}",
                        exc_info=True,
                    )
                    # Just stop the stream
                    return

                except Exception as e:
                    stream_duration = (
                        asyncio.get_event_loop().time() - stream_start_time
                    )
                    logger.error(
                        f"[{request_id}] Unexpected streaming error after {stream_duration:.2f}s: {str(e)}",
                        exc_info=True,
                    )
                    # Just stop the stream
                    return

            return StreamingResponse(
                stream_response(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "X-Accel-Buffering": "no",  # Disable buffering in nginx
                },
            )

        # For non-streaming requests, use regular response
        else:
            logger.debug(f"[{request_id}] Making non-streaming request")

            request_start_time = asyncio.get_event_loop().time()
            resp = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=req_body,
            )
            request_duration = asyncio.get_event_loop().time() - request_start_time

            # Log response details
            logger.info(
                f"[{request_id}] Response received: status={resp.status_code}, size={len(resp.content):,} bytes, time={request_duration:.2f}s"
            )
            logger.debug(f"[{request_id}] Response headers: {dict(resp.headers)}")

            # Filter headers that would conflict with FastAPI's response handling
            # These headers are managed by the framework and passing them through can cause issues
            filtered_headers = {
                k: v
                for k, v in resp.headers.items()
                if k.lower()
                not in [
                    "content-encoding",  # FastAPI handles encoding
                    "transfer-encoding",  # FastAPI handles chunked responses
                    "content-length",  # FastAPI calculates this
                    "connection",  # FastAPI manages connections
                ]
            }

            return Response(
                content=resp.content,
                status_code=resp.status_code,
                headers=filtered_headers,
                media_type=resp.headers.get("content-type"),
            )

    except httpx.HTTPStatusError as e:
        # This is an actual HTTP error response (4xx, 5xx)
        request_duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            f"[{request_id}] HTTP status error after {request_duration:.2f}s: {str(e)}",
            exc_info=True,
        )
        # Pass through the exact status code and response
        return Response(
            content=e.response.content,
            status_code=e.response.status_code,
            headers=dict(e.response.headers),
            media_type=e.response.headers.get("content-type"),
        )

    except httpx.TimeoutException as e:
        request_duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            f"[{request_id}] Timeout after {request_duration:.2f}s: {str(e)}",
            exc_info=True,
        )
        # Standard Gateway Timeout
        return Response(
            content=str(e), status_code=504, headers={"Content-Type": "text/plain"}
        )

    except httpx.RequestError as e:
        # This catches all request errors including ConnectError, etc.
        request_duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            f"[{request_id}] Request error after {request_duration:.2f}s: {str(e)}",
            exc_info=True,
        )
        # For any request error, return 502 Bad Gateway with the original error message
        return Response(
            content=str(e), status_code=502, headers={"Content-Type": "text/plain"}
        )

    except Exception as e:
        request_duration = asyncio.get_event_loop().time() - start_time
        logger.error(
            f"[{request_id}] Unexpected error after {request_duration:.2f}s: {str(e)}",
            exc_info=True,
        )
        # For truly unexpected errors, return 500
        return Response(
            content=str(e), status_code=500, headers={"Content-Type": "text/plain"}
        )


@app.on_event("shutdown")
async def shutdown_event():
    await client.aclose()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8666)
