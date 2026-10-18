from urllib.parse import quote_plus
from http_methods import HttpMethod


class RawHttpPacket:
    MULTIPART_DELIMITER = "----CustomFormBoundary7f9a8b2c4d1e"
    DEFAULT_USER_TOKEN = "1153e179bbb8d48ddd72e9f8c452c2bb"

    def __init__(self, target_host: str, url_path: str, http_method: HttpMethod, payload: bytes = b""):
        self._host = target_host
        self._url = url_path
        self._method = http_method
        self._payload = payload
        self._query_items: list[str] = []
        self._cookie_jar: dict[str, str] = {"user": self.DEFAULT_USER_TOKEN}
        self._header_map: dict[str, str] = {
            self._format_header_name("host"): target_host
        }

        if self._payload:
            self._sync_content_length()

    @staticmethod
    def _format_header_name(raw_name: str) -> str:
        return "-".join(part.capitalize() for part in raw_name.split("-"))

    def _sync_content_length(self) -> None:
        key = self._format_header_name("content-length")
        self._header_map[key] = str(len(self._payload))

    def set_header(self, name: str, val: str) -> None:
        self._header_map[name] = val

    def append_query_param(self, key: str, val: str) -> None:
        self._query_items.append(f"{quote_plus(key)}={quote_plus(val)}")

    def append_cookie(self, key: str, val: str) -> None:
        self._cookie_jar[key] = val

    def append_urlencoded_field(self, key: str, val: str) -> None:
        ct_key = self._format_header_name("content-type")
        current_ct = self._header_map.get(ct_key, "")

        if "multipart/form-data" in current_ct:
            tail = f"--{self.MULTIPART_DELIMITER}--\r\n".encode("utf-8")
            if self._payload.endswith(tail):
                self._payload = self._payload[:-len(tail)]

            part_header = (
                f"--{self.MULTIPART_DELIMITER}\r\n"
                f'Content-Disposition: form-data; name="{key}"\r\n\r\n'
            ).encode("utf-8")

            self._payload += part_header + val.encode("utf-8") + b"\r\n" + tail
        else:
            self._header_map.setdefault(ct_key, "application/x-www-form-urlencoded")
            pair_bytes = f"{quote_plus(key)}={quote_plus(val)}".encode("utf-8")
            self._payload = pair_bytes if not self._payload else self._payload + b"&" + pair_bytes

        self._sync_content_length()

    def append_multipart_file(self, field_name: str, text_data: str) -> None:
        ct_key = self._format_header_name("content-type")
        self._header_map[ct_key] = f"multipart/form-data; boundary={self.MULTIPART_DELIMITER}"

        tail = f"--{self.MULTIPART_DELIMITER}--\r\n".encode("utf-8")
        if self._payload.endswith(tail):
            self._payload = self._payload[:-len(tail)]

        part_header = (
            f"--{self.MULTIPART_DELIMITER}\r\n"
            f'Content-Disposition: form-data; name="{field_name}"; filename="{field_name}"\r\n'
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode("utf-8")

        self._payload += part_header + text_data.encode("utf-8") + b"\r\n" + tail
        self._sync_content_length()

    def build_raw_packet(self) -> bytes:
        full_path = self._url
        if self._query_items:
            sep = "&" if "?" in full_path else "?"
            full_path = f"{full_path}{sep}{'&'.join(self._query_items)}"

        cookie_header_key = self._format_header_name("cookie")
        self._header_map[cookie_header_key] = "; ".join(
            f"{k}={v}" for k, v in self._cookie_jar.items()
        )

        lines = [f"{self._method.value} {full_path} HTTP/1.1"]
        lines.extend(f"{k}: {v}" for k, v in self._header_map.items())
        header_block = "\r\n".join(lines) + "\r\n\r\n"

        return header_block.encode("utf-8") + self._payload