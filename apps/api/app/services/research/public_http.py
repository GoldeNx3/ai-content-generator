"""HTTP transport that connects only to the public IPs it actually validated.

The request URL remains unchanged, preserving the HTTP Host header and TLS SNI.
"""

import asyncio
import ipaddress
import socket
import ssl

import httpcore
import httpx


class PublicNetworkBackend(httpcore.AsyncNetworkBackend):
    def __init__(self, backend=None) -> None:
        self.backend = backend or httpcore.AnyIOBackend()

    async def connect_tcp(self, host, port, timeout=None, local_address=None, socket_options=None):
        try:
            literal = ipaddress.ip_address(host)
        except ValueError:
            literal = None
        if literal is not None:
            addresses = [str(literal)]
        else:
            try:
                records = await asyncio.wait_for(
                    asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
                    timeout=timeout,
                )
            except (OSError, TimeoutError) as exc:
                raise httpcore.ConnectError("Source DNS resolution failed") from exc
            addresses = list(dict.fromkeys(record[4][0] for record in records))
        if not addresses or any(not ipaddress.ip_address(address).is_global for address in addresses):
            raise httpcore.ConnectError("Source must resolve to public addresses")
        error = None
        for address in addresses:
            try:
                # Pin the connection to this numeric IP; no second hostname lookup.
                return await self.backend.connect_tcp(address, port, timeout=timeout,
                    local_address=local_address, socket_options=socket_options)
            except (httpcore.ConnectError, httpcore.ConnectTimeout) as exc:
                error = exc
        raise error

    async def connect_unix_socket(self, *args, **kwargs):
        raise httpcore.ConnectError("Unix sockets are not public sources")

    async def sleep(self, seconds):
        await self.backend.sleep(seconds)


class PublicHTTPTransport(httpx.AsyncHTTPTransport):
    def __init__(self) -> None:
        super().__init__(trust_env=False)
        # HTTPX exposes transport injection, while HTTPcore exposes network backend injection.
        # Keep the adapter here so the rest of the extractor uses ordinary HTTPX streams.
        self._pool = httpcore.AsyncConnectionPool(
            ssl_context=ssl.create_default_context(), network_backend=PublicNetworkBackend(),
            max_connections=10, max_keepalive_connections=5, keepalive_expiry=5,
        )
