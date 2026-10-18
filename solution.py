import socket
import time
import requests
from bs4 import BeautifulSoup

from http_methods import HttpMethod
from http_request import RawHttpPacket
from task_parser import HtmlTaskExtractor


class QuestRunner:
    TARGET_HOST = "hw1.alexbers.com"
    TARGET_PORT = 80
    BASE_ENDPOINT = f"http://{TARGET_HOST}"
    USER_TOKEN = "1153e179bbb8d48ddd72e9f8c452c2bb"

    @classmethod
    def _build_full_url(cls, endpoint: str) -> str:
        clean_path = endpoint if endpoint.startswith("/") else f"/{endpoint}"
        return f"{cls.BASE_ENDPOINT}{clean_path}"

    @staticmethod
    def _check_and_print_secret(html_text: str) -> bool:
        if "секретный ключ" in html_text.lower():
            dom = BeautifulSoup(html_text, "html.parser")
            code_node = dom.find("code")
            if code_node:
                print(f"\nУСПЕХ! Секретный ключ: {code_node.get_text(strip=True)}")
            return True
        return False

    @staticmethod
    def _read_http_frame(conn: socket.socket) -> str:
        buffer = bytearray()
        delimiter = b"\r\n\r\n"

        while delimiter not in buffer:
            piece = conn.recv(1024)
            if not piece:
                break
            buffer.extend(piece)

        if delimiter not in buffer:
            return buffer.decode("utf-8", errors="replace")

        raw_head, raw_body = buffer.split(delimiter, 1)
        head_str = raw_head.decode("utf-8", errors="replace")

        expected_len = 0
        for row in head_str.split("\r\n"):
            if row.lower().startswith("content-length:"):
                expected_len = int(row.partition(":")[2].strip())
                break

        remaining = expected_len - len(raw_body)
        while remaining > 0:
            piece = conn.recv(min(1024, remaining))
            if not piece:
                break
            raw_body.extend(piece)
            remaining -= len(piece)

        return (raw_head + delimiter + raw_body).decode("utf-8", errors="replace")

    @classmethod
    def run_raw_sockets(cls) -> None:
        packet = RawHttpPacket(cls.TARGET_HOST, "/", HttpMethod.GET)
        conn = socket.create_connection((cls.TARGET_HOST, cls.TARGET_PORT), timeout=10)
        step_counter = 0

        while True:
            while True:
                try:
                    conn.sendall(packet.build_raw_packet())
                    raw_reply = cls._read_http_frame(conn)
                    if raw_reply:
                        break
                except (TimeoutError, socket.timeout, ConnectionError, OSError):
                    pass
                conn.close()
                conn = socket.create_connection((cls.TARGET_HOST, cls.TARGET_PORT), timeout=10)

            step_counter += 1
            print(f"Выполнено шагов (сокеты): {step_counter}")

            if cls._check_and_print_secret(raw_reply):
                conn.close()
                break

            step_info = HtmlTaskExtractor.extract(raw_reply)
            packet = RawHttpPacket(cls.TARGET_HOST, step_info.endpoint, step_info.method)

            for file_name, file_body in step_info.attachments.items():
                packet.append_multipart_file(file_name, file_body)
            for f_name, f_val in step_info.form_fields.items():
                packet.append_urlencoded_field(f_name, f_val)

            for h_name, h_val in step_info.headers.items():
                packet.set_header(h_name, h_val)
            for c_name, c_val in step_info.cookies.items():
                packet.append_cookie(c_name, c_val)
            for p_name, p_val in step_info.query_params.items():
                packet.append_query_param(p_name, p_val)

            time.sleep(0.1)

    @classmethod
    def run_requests_lib(cls) -> None:
        session = requests.Session()
        session.cookies.set("user", cls.USER_TOKEN)
        while True:
            try:
                resp = session.get(
                    cls._build_full_url("/"),
                    headers={"Connection": "close"},
                    timeout=8,
                )
                break
            except requests.exceptions.RequestException:
                time.sleep(0.5)

        step_counter = 0

        while True:
            step_counter += 1
            page_text = resp.content.decode("utf-8", errors="replace")
            print(f"Выполнено шагов (requests): {step_counter}")

            if cls._check_and_print_secret(page_text):
                break

            step_info = HtmlTaskExtractor.extract(page_text)

            current_headers = {"Connection": "close"}
            current_headers.update(step_info.headers)

            multipart_files = (
                {fname: (fname, fbody.encode("utf-8")) for fname, fbody in step_info.attachments.items()}
                if step_info.attachments
                else None
            )

            while True:
                try:
                    resp = session.request(
                        method=step_info.method.value,
                        url=cls._build_full_url(step_info.endpoint),
                        params=step_info.query_params or None,
                        data=step_info.form_fields or None,
                        files=multipart_files,
                        headers=current_headers,
                        cookies=step_info.cookies or None,
                        timeout=8,
                    )
                    break
                except requests.exceptions.RequestException as err:
                    print(f" [!] Ошибка сети ({err}), повторяем запрос...")
                    time.sleep(0.5)

            time.sleep(0.05)