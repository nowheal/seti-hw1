import html as html_lib
import re
from urllib.parse import urljoin
import requests

from http_request import HttpRequest


class Solution:
    """Управляет прохождением теста"""

    def __init__(self, base_url: str, token: str):
        self.base_url = base_url
        self.token = token
        self.session = requests.Session()

    def parse_table(self, html: str, keyword: str) -> list[tuple[str, str]]:
        pos = html.lower().find(keyword.lower())
        match = (
            re.search(r"<table[^>]*>(.*?)</table>", html[pos:], re.S | re.I)
            if pos != -1
            else None
        )
        if not match:
            return []
        rows = re.findall(r"<tr[^>]*>(.*?)</tr>", match.group(1), re.S | re.I)
        cells = [
            re.findall(r"<td[^>]*>(.*?)</td>", r, re.S | re.I) for r in rows
        ]
        clean = lambda s: html_lib.unescape(re.sub(r"<[^>]+>", "", s)).strip()
        return [(clean(c[0]), clean(c[1])) for c in cells if len(c) >= 2]

    def build_request(self, html: str) -> HttpRequest:
        req = HttpRequest()
        req.cookies = {"user": self.token, **dict(self.parse_table(html, "cookie"))}
        req.headers = dict(self.parse_table(html, "заголовк"))
        req.params = dict(self.parse_table(html, "параметры запроса"))

        action = re.search(r"по адресу\s+<code>([^<]+)</code>", html, re.I)

        if "Загрузите файлы" in html:
            req.method, req.path = "POST", action.group(1).strip()
            req.files = [
                (fn, (fn, c.encode("utf-8")))
                for fn, c in self.parse_table(html, "файл")
            ]
        elif "Отправьте POST-запрос" in html:
            req.method, req.path = "POST", action.group(1).strip()
            req.data = dict(self.parse_table(html, "данные формы"))
        else:
            link = re.search(r"href=['\"]([^'\"]+)['\"]", html, re.I)
            req.path = (
                link.group(1).strip()
                if link
                else (action.group(1).strip() if action else "/")
            )

        return req

    def run(self):
        url = self.base_url + "/"
        self.session.cookies.set("user", self.token)
        resp = self.session.get(url)

        step = 1
        while True:
            html = resp.text
            print(f"--- Шаг {step} | URL: {url} ---")
            if "секрет" in html.lower() or "secret" in html.lower():
                print("\n" + "=" * 50)
                print("СЕКРЕТ ПОЛУЧЕН:")
                print("=" * 50)
                print(html)
                break

            req = self.build_request(html)
            self.session.cookies.clear()
            for k, v in req.cookies.items():
                self.session.cookies.set(k, v)

            kwargs = {}
            if req.files:
                kwargs["files"] = req.files
            if req.data:
                kwargs["data"] = req.data

            url = urljoin(self.base_url, req.path)
            resp = self.session.request(
                req.method, url, headers=req.headers, params=req.params, **kwargs
            )
            resp.encoding = "utf-8"
            step += 1