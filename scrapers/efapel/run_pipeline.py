import json
import logging
from datetime import datetime

from .crawler import EfapelCrawler
from .extractor import EfapelExtractor

logger = logging.getLogger(__name__)


class EfapelPipeline:
    """
    Pipeline:
    crawler -> extractor -> normalization -> storage
    """

    def __init__(self, crawler, extractor):
        self.crawler = crawler
        self.extractor = extractor

    def run(self, output_file=None):
        """
        Execute the full pipeline and save JSON output.
        """

        logger.info("Starting Efapel pipeline")

        gama_links = self.crawler.get_gama_links()
        subcategory_links = []

        for gama_link in gama_links:
            subcategory_links.extend(self.crawler.get_subcategory_links(gama_link))

        product_urls = []
        for subcategory_url in subcategory_links:
            logger.info("Found subcategory: %s", subcategory_url)
            product_urls.extend(self.crawler.get_product_links(subcategory_url))

        logger.info("Found %s product pages", len(product_urls))

        all_products = []

        for index, url in enumerate(product_urls, start=1):
            if any(
                blocked in url
                for blocked in [
                    "informacoes-tecnicas",
                    "outros-documentos",
                    "video-tutorial",
                    "simulador",
                    "acabamentos",
                ]
            ):
                continue

            logger.info("[%s/%s] Processing: %s", index, len(product_urls), url)

            try:
                html = self.crawler.get_html(url)
                extracted_products = self.extractor.extract(html, url)
                all_products.extend(extracted_products)
            except Exception as exc:
                logger.exception("Error while processing %s: %s", url, exc)

        if output_file is None:
            output_file = f"efapel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        self._save(output_file, all_products)
        logger.info("Pipeline finished -> %s", output_file)
        return all_products

    def _save(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def _normalize_main(self, product):
        return {
            "name": self._clean_text(product.name),
            "description": self._clean_text(product.description),
            "sku": self._clean_text(product.sku),
            "colors": self._clean_colors(product.colors),
            "images": product.images,
            "type": "main",
        }

    def _merge_variant(self, main, variant):
        return {
            "name": f"{main['name']} - {self._clean_text(variant.name)}",
            "description": main["description"],
            "sku": self._clean_text(variant.sku) or main["sku"],
            "colors": self._clean_colors(variant.colors) or main["colors"],
            "images": variant.images or main["images"],
            "type": "variant",
            "parent_sku": main["sku"],
        }

    def _clean_text(self, value):
        if not value:
            return None
        return " ".join(str(value).split())

    def _clean_colors(self, colors):
        if not colors:
            return None

        if isinstance(colors, list):
            return [color.strip() for color in colors if color.strip()]

        if isinstance(colors, str):
            if colors == "-":
                return None
            return colors.split()

        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    crawler = EfapelCrawler()
    extractor = EfapelExtractor()
    pipeline = EfapelPipeline(crawler, extractor)
    result = pipeline.run()

    print("\n=== PIPELINE RESULT ===")
    print(result)
