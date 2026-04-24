from bs4 import BeautifulSoup


class BaseHtmlParser:
    def __init__(self, html):
        self.soup = BeautifulSoup(html, "html.parser")

    def select(self, css):
        return self.soup.select(css)

    def select_one(self, css):
        return self.soup.select_one(css)

    def text(self, css):
        element = self.select_one(css)
        return element.get_text(" ", strip=True) if element else None

    def html(self, css):
        element = self.select_one(css)
        return str(element) if element else None

    def attribute(self, css, attribute_name):
        element = self.select_one(css)
        if not element:
            return None
        return element.get(attribute_name)
