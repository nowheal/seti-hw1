import html as html_lib
import re
from urllib.parse import quote

from raw_client import RawHttpClient

HOST = "hw1.alexbers.com"
PORT = 80
TOKEN = "1153e179bbb8d48ddd72e9f8c452c2bb"


class RawSolution:
    """Класс парсит страницы и прогоняет через сокеты"""

    def __init__(self, host: str, port: int, token: str):
        self.host = host
        self.token = token
        self.client = RawHttpClient(host, port)

    @staticmethod
    def _clean_html(text: str) -> str:
        return html_lib.unescape(re.sub(r"<[^>]+>", "", text)).strip()

    def parse_table_rows(
        self, html: str, keyword: str
    ) -> list[tuple[str, str]]:
        pos = html.lower().find(keyword.lower())
        if pos == -1:
            return []

        match = re.search(
            r"<table[^>]*>(.*?)</table>", html[pos:], flags=re.DOTALL | re.IGNORECASE
        )
        if not match:
            return []

        pairs = []
        for row in re.findall(
            r"<tr[^>]*>(.*?)</tr>", match.group(1), flags=re.DOTALL | re.IGNORECASE
        ):
            cells = re.findall(
                r"<td[^>]*>(.*?)</td>", row, flags=re.DOTALL | re.IGNORECASE
            )
            if len(cells) >= 2:
                pairs.append(
                    (self._clean_html(cells[0]), self._clean_html(cells[1]))
                )
        return pairs

    @staticmethod
    def build_multipart(
        files: list[tuple[str, str]], boundary: str
    ) -> tuple[dict, bytes]:
        """Собирает файлы для отправки"""
        body = b""
        for fname, content in files:
            body += (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="{fname}"; filename="{fname}"\r\n'
                f"Content-Type: text/plain; charset=utf-8\r\n\r\n"
                f"{content}\r\n"
            ).encode("utf-8")
        body += f"--{boundary}--\r\n".encode("utf-8")
        return {"Content-Type": f"multipart/form-data; boundary={boundary}"}, body

    def run(self):
        current_path = "/"
        step = 1

        html = self.client.send_request("GET", current_path, {}, {"user": self.token})

        while True:
            print(f"--- Шаг {step} [RAW Sockets]: {current_path} ---")

            if "секрет" in html.lower() or "secret" in html.lower():
                print("\n" + "=" * 50)
                print("СЕКРЕТ ПОЛУЧЕН:")
                print("=" * 50)
                print(html)
                break

            cookies = {"user": self.token, **dict(self.parse_table_rows(html, "cookie"))}
            headers = dict(self.parse_table_rows(html, "заголовк"))
            params = self.parse_table_rows(html, "параметры запроса")

            if "Загрузите файлы" in html:
                method = "POST"
                files = self.parse_table_rows(html, "файл")
                part_headers, body = self.build_multipart(
                    files, "----CustomSocketBoundary12345"
                )
                headers.update(part_headers)
                action = re.search(r"по адресу\s+<code>([^<]+)</code>", html, re.I)
                target_path = action.group(1).strip()

            elif "Отправьте POST-запрос" in html:
                method = "POST"
                form_data = self.parse_table_rows(html, "данные формы")
                body = "&".join(
                    f"{quote(k)}={quote(v)}" for k, v in form_data
                ).encode("utf-8")
                headers["Content-Type"] = (
                    "application/x-www-form-urlencoded; charset=utf-8"
                )
                action = re.search(r"по адресу\s+<code>([^<]+)</code>", html, re.I)
                target_path = action.group(1).strip()

            elif "Отправьте GET-запрос" in html:
                method = "GET"
                body = b""
                action = re.search(r"по адресу\s+<code>([^<]+)</code>", html, re.I)
                target_path = action.group(1).strip()

            else:
                method = "GET"
                body = b""
                link = re.search(r"href=['\"]([^'\"]+)['\"]", html, re.I)
                target_path = link.group(1).strip() if link else "/"

            if params:
                query_str = "&".join(f"{quote(k)}={quote(v)}" for k, v in params)
                target_path += f"?{query_str}"

            html = self.client.send_request(
                method, target_path, headers, cookies, body
            )
            current_path = target_path
            step += 1


if __name__ == "__main__":
    solution = RawSolution(HOST, PORT, TOKEN)
    solution.run()
