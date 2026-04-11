from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .urls import BASE_URL


class GolmarParser:

    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "html.parser")

    def text(self, selector: str):
        el = self.soup.select_one(selector)
        return el.get_text(strip=True) if el else ""

    def html(self, selector: str):
        el = self.soup.select_one(selector)
        return el.decode_contents() if el else ""

    def all_links(self):
        links = set()
        for a in self.soup.find_all("a", href=True):
            links.add(urljoin(BASE_URL, a["href"]))
        return links

    def images(self):
        imgs = []
        for img in self.soup.select(".product-image img"):
            if img.get("src"):
                imgs.append(urljoin(BASE_URL, img["src"]))
        return imgs