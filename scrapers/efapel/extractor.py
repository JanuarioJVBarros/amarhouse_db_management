from urllib.parse import urlparse, urljoin
from typing import List

from scrapers.base import build_scraped_product, slugify
from .parser import EfapelParser
from ..models import ScrapedProduct


class EfapelExtractor:
    def extract(self, html: str, url: str) -> List[ScrapedProduct]:
        parser = EfapelParser(html)
        extracted_products = []

        rows = parser.select("tr.row")

        for row in rows:
            if row.find("th"):
                continue
            extracted_products.extend(self.parse_products_from_row(row, url))

        return extracted_products
    
    def _parse_item(self, container, url: str, side: str) -> ScrapedProduct | None:

        name_el = container.select_one("h4")
        if not name_el:
            return None

        name = name_el.get_text(" ", strip=True)

        # description is only in main product
        desc_el = container.select_one("td p")
        description = None
        if desc_el and side == "main":
            description = desc_el.get_text(" ", strip=True)

        # ref
        ref_el = container.select_one(".ref")
        reference = ref_el.get_text(" ", strip=True) if ref_el else None

        # colors
        color_el = container.select_one(".color")
        colors = None
        if color_el:
            colors = color_el.get_text(" ", strip=True).split(" ")

        # image
        img_el = container.select_one("img")
        image = img_el["src"] if img_el and img_el.get("src") else None
        if image:
            image = urljoin(url, image)

        slug = urlparse(url).path.split("/")[-1]

        return build_scraped_product(
            name=name,
            slug=slug,
            description=description,
            reference=reference,
            images=[image] if image else [],
            labels=[side],  # "main" or "variant"
            source_url=url,
            colors=colors,
            supplier="efapel",
        )
    
    def parse_products_from_row(self, row, url):
        products: List[ScrapedProduct] = []

        # get all inner product rows (left + right columns mixed)
        inner_rows = row.select("td.column table tr")

        for tr in inner_rows:
            name_el = tr.select_one("h4")
            ref_el = tr.select_one("td.ref p")

            # skip invalid rows (headers / empty rows)
            if not name_el or not ref_el:
                continue

            name = name_el.get_text(strip=True)
            slug = slugify(name)

            desc_el = tr.select_one("td:not(.ref):not(.color) p")
            description = desc_el.get_text(" ", strip=True) if desc_el else ""

            ref = ref_el.get_text(strip=True)

            color_el = tr.select_one("td.color p")
            colors = color_el.get_text(" ", strip=True).split(" ") if color_el else ["-"]

            image_el = tr.select_one("td.image img")
            image = image_el["src"] if image_el and image_el.get("src") else None
            if image:
                image = urljoin(url, image)

            color_variants = []
            for color in colors:
                color_variant_name = f"{name} - {color}"
                sku_with_color = f"{ref}{color}"
                if color == "-":
                    color_variant_name = name
                    color = None
                    sku_with_color = ref
                color_variants.append({
                    "name": color_variant_name,
                    "price": 0,  # price is not provided on the page
                    "sku": sku_with_color,
                    "option": color,
                })

            main_product = build_scraped_product(
                name=name,
                slug=slug,
                description=description,
                images=[image] if image else [],
                labels=["127"],
                option_groups=[{"name": "Cor", "options": colors}],
                variants=color_variants,
                source_url=url,
                supplier="efapel",
            )
            
            products.append(main_product)
        return products
