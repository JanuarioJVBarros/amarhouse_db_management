from bs4 import BeautifulSoup


class EfapelParser:
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "html.parser")

    def select(self, css: str):
        return self.soup.select(css)

    def text(self, css: str):
        el = self.soup.select_one(css)
        return el.get_text(" ", strip=True) if el else None

    def html(self, css: str):
        el = self.soup.select_one(css)
        return str(el) if el else None