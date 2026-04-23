import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .urls import BASE_URL, CATEGORY_LIST


class EfapelCrawler:
    def __init__(self, base_url=BASE_URL):
        self.base_url = base_url

    def get_html(self, url):
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.text

    # get the main category links from the products landing page (Gamas)
    def get_gama_links(self):
        url = f"{BASE_URL}/produtos"
        html = self.get_html(url)
        soup = BeautifulSoup(html, "html.parser")

        links = []
        for a in soup.select("a.category[href]"):
            href = urljoin(BASE_URL, a["href"])
            for cat in CATEGORY_LIST:
                if cat in href:
                    links.append(href)
                    break

        return links

    # get subcategory links from a gama page (e.g. Logus 90)
    def get_subcategory_links(self, gama_url):
        html = self.get_html(gama_url)
        soup = BeautifulSoup(html, "html.parser")

        subcategory_links = []

        for a in soup.select("a.subcategory[href]"):
            href = urljoin(BASE_URL, a["href"])
            name = a.get_text(" ", strip=True)

            # skip documentation pages
            if "informacoes-tecnicas" in href or "outros-documentos" in href or "video-tutorial" in href or "simulador" in href or "acabamentos" in href:
                continue

            # skip self-links
            if href.rstrip("/") == gama_url.rstrip("/"):
                continue

            subcategory_links.append(href)

        # deduplicate (stable order preserved)
        seen = set()
        unique_links = []

        for link in subcategory_links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)

        return unique_links

    # get product links from a category or subcategory page (e.g. Logus 90 Controlo de Temperatura)
    def get_product_links(self, category_url):
        """
        Extracts product category and subcategory links from Efapel structure.
        Handles both:
        - Main categories (h4)
        - Subcategories (h5 inside nested lists)
        """

        html = self.get_html(category_url)
        soup = BeautifulSoup(html, "html.parser")


        product_links = set()

        main_categories = soup.select("a.subcategory h4")
        for tag in main_categories:
            a_tag = tag.find_parent("a")
            if a_tag and a_tag.get("href"):
                product_links.add(urljoin(BASE_URL, a_tag["href"]))

        sub_categories = soup.select("a.subcategory h5")
        for tag in sub_categories:
            a_tag = tag.find_parent("a")
            if a_tag and a_tag.get("href"):
                product_links.add(urljoin(BASE_URL, a_tag["href"]))

        return list(product_links)
    
