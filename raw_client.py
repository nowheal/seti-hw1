import socket


class RawHttpClient:
    """Keep-Alive HTTP"""

    def __init__(self, host: str, port: int = 80):
        self.host = host
        self.port = port
        self.sock = None
        self._connect()

    def _connect(self):
        """Открывает TCP-соединение"""
        if self.sock:
            try:
                self.sock.close()
            except Exception:
                pass
        self.sock = socket.create_connection((self.host, self.port), timeout=10)

    def send_request(
        self,
        method: str,
        path: str,
        headers: dict,
        cookies: dict,
        body: bytes = b"",
    ) -> str:
        """Отправляет сырой HTTP-запрос"""
        lines = [
            f"{method} {path} HTTP/1.1",
            f"Host: {self.host}",
            "Connection: keep-alive",
        ]

        if cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in cookies.items())
            lines.append(f"Cookie: {cookie_str}")

        for k, v in headers.items():
            lines.append(f"{k}: {v}")

        lines.append(f"Content-Length: {len(body)}")

        request_bytes = (
            "\r\n".join(lines).encode("utf-8") + b"\r\n\r\n" + body
        )

        for _ in range(2):
            try:
                self.sock.sendall(request_bytes)
                break
            except (socket.error, BrokenPipeError):
                self._connect()

        raw_response = b""
        while b"\r\n\r\n" not in raw_response:
            chunk = self.sock.recv(1024)
            if not chunk:
                break
            raw_response += chunk

        headers_part, _, remaining_body = raw_response.partition(b"\r\n\r\n")

        content_len = 0
        for header_line in headers_part.decode("latin-1").split("\r\n"):
            if header_line.lower().startswith("content-length:"):
                content_len = int(header_line.split(":", 1)[1].strip())
                break

        body_bytes = remaining_body
        while len(body_bytes) < content_len:
            needed = content_len - len(body_bytes)
            chunk = self.sock.recv(min(4096, needed))
            if not chunk:
                break
            body_bytes += chunk

        return body_bytes.decode("utf-8", errors="replace")