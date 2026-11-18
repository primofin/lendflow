"""Reject oversized requests before they are buffered (LF-005).

FastAPI parses a multipart body before it runs authentication, so without a cap anyone could
make the server spool an arbitrarily large upload to disk. This pure-ASGI middleware refuses
a request whose Content-Length is over the limit, and also counts the bytes of chunked bodies
that declare no length. The exact per-file limit and its friendly message live in
document_service; this is the coarse outer guard.
"""

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.config import get_settings


class _TooLarge(Exception):
    pass


class RequestSizeLimitMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        settings = get_settings()
        limit = settings.max_upload_bytes + settings.max_request_overhead_bytes
        declared = dict(scope["headers"]).get(b"content-length")
        if declared and declared.isdigit() and int(declared) > limit:
            await self._reject(send)
            return

        received = 0

        async def counting_receive() -> Message:
            nonlocal received
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > limit:
                    raise _TooLarge
            return message

        started = False

        async def tracking_send(message: Message) -> None:
            nonlocal started
            if message["type"] == "http.response.start":
                started = True
            await send(message)

        try:
            await self.app(scope, counting_receive, tracking_send)
        except _TooLarge:
            if not started:
                await self._reject(send)

    @staticmethod
    async def _reject(send: Send) -> None:
        limit_mb = get_settings().max_upload_bytes // (1024 * 1024)
        body = f'{{"detail":"The request is too large. Files must be {limit_mb} MB or smaller."}}'
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"connection", b"close"),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body.encode()})
