class HttpRequest:
    """Параметры HTTP-запроса"""

    def __init__(self, method: str = "GET", path: str = "/"):
        self.method = method
        self.path = path
        self.headers = {}
        self.params = {}
        self.cookies = {}
        self.data = {}
        self.files = []