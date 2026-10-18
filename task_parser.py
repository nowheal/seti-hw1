from dataclasses import dataclass, field
from bs4 import BeautifulSoup, Tag
from http_methods import HttpMethod


@dataclass
class TaskStep:
    method: HttpMethod = HttpMethod.GET
    endpoint: str = ""
    query_params: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)
    form_fields: dict[str, str] = field(default_factory=dict)
    attachments: dict[str, str] = field(default_factory=dict)


class HtmlTaskExtractor:
    @staticmethod
    def _find_section_label(table_node: Tag) -> str:
        node = table_node.previous_element
        while node is not None:
            if isinstance(node, str):
                cleaned = node.strip()
                if cleaned:
                    return cleaned.lower()
            node = node.previous_element
        return ""

    @staticmethod
    def _extract_key_values(table_node: Tag) -> dict[str, str]:
        extracted: dict[str, str] = {}
        for tr in table_node.select("tr"):
            cells = tr.find_all(["td", "th"])
            if len(cells) == 2 and cells[0].name == "td":
                k, v = cells[0].get_text(strip=True), cells[1].get_text(strip=True)
                extracted[k] = v
        return extracted

    @classmethod
    def extract(cls, raw_payload: str) -> TaskStep:
        html_part = raw_payload.split("\r\n\r\n", 1)[-1]
        doc = BeautifulSoup(html_part, "html.parser")
        step = TaskStep()

        page_content = (doc.body.get_text() if doc.body else doc.get_text()).lower()
        if any(marker in page_content for marker in ("post-запрос", "загрузите файл")):
            step.method = HttpMethod.POST
        elif "get-запрос" in page_content:
            step.method = HttpMethod.GET

        anchor = doc.find("a", href=True)
        if anchor:
            step.endpoint = anchor["href"]
        else:
            code_elem = doc.find("code")
            if code_elem and code_elem.get_text(strip=True).startswith("/"):
                step.endpoint = code_elem.get_text(strip=True)

        for tbl in doc.find_all("table"):
            label = cls._find_section_label(tbl)
            kv_data = cls._extract_key_values(tbl)
            header_cells = " ".join(th.get_text(strip=True).lower() for th in tbl.find_all("th"))

            if "файл" in label or "файл" in header_cells:
                step.attachments = kv_data
            elif "параметр" in label or "параметр" in header_cells:
                step.query_params = kv_data
            elif "cookie" in label or "cookie" in header_cells:
                step.cookies = kv_data
            elif "заголовк" in label or "заголовок" in header_cells:
                step.headers = kv_data
            elif "формы" in label or "данные формы" in label:
                step.form_fields = kv_data

        return step