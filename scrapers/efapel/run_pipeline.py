from .crawler import EfapelCrawler
from .extractor import EfapelExtractor
import json
from datetime import datetime

class EfapelPipeline:
    """
    Pipeline:
    Crawler → Extractor → Cleaner → Storage
    """

    def __init__(self, crawler, extractor):
        self.crawler = crawler
        self.extractor = extractor

    # -----------------------------
    # MAIN ENTRY POINT
    # -----------------------------
    def run(self, output_file=None):
        """
        Executes full pipeline and saves JSON output.
        """

        print("🚀 Starting Efapel pipeline...")

        gama_links = self.crawler.get_gama_links()
        subcategory_links = []
        for gama_link in gama_links:
            subcategory_links.extend(self.crawler.get_subcategory_links(gama_link))
        product_urls = []
        for sub in subcategory_links:
            print(f"🔍 Found subcategory: {sub}")
            product_urls.extend(self.crawler.get_product_links(sub))
        print(f"📦 Found {len(product_urls)} product pages")

        all_products = []

        for i, url in enumerate(product_urls, 1):
            #    skip documentation pages
            if "informacoes-tecnicas" in url or "outros-documentos" in url or "video-tutorial" in url or "simulador" in url or "acabamentos" in url:
                continue
            print(f"[{i}/{len(product_urls)}] Processing: {url}")

            try:
                html = self.crawler.get_html(url)

                extracted_products = self.extractor.extract(html, url)

                all_products.extend(extracted_products)

            except Exception as e:
                print(f"❌ Error on {url}: {e}")

        if output_file is None:
            output_file = f"efapel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        self._save(output_file, all_products)

        print(f"✅ Pipeline finished → {output_file}")

        return all_products


    # -----------------------------
    # SAVE
    # -----------------------------
    def _save(self, file_path, data):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    # -----------------------------
    # NORMALIZATION HELPERS
    # -----------------------------
    def _normalize_main(self, product):
        return {
            "name": self._clean_text(product.name),
            "description": self._clean_text(product.description),
            "sku": self._clean_text(product.sku),
            "colors": self._clean_colors(product.colors),
            "images": product.images,
            "type": "main"
        }

    def _merge_variant(self, main, variant):
        return {
            "name": f"{main['name']} - {self._clean_text(variant.name)}",
            "description": main["description"],
            "sku": self._clean_text(variant.sku) or main["sku"],
            "colors": self._clean_colors(variant.colors) or main["colors"],
            "images": variant.images or main.images,
            "type": "variant",
            "parent_sku": main["sku"]
        }

    def _clean_text(self, value):
        if not value:
            return None
        return " ".join(str(value).split())

    def _clean_colors(self, colors):
        if not colors:
            return None

        if isinstance(colors, list):
            return [c.strip() for c in colors if c.strip()]

        if isinstance(colors, str):
            if colors == "-":
                return None
            return colors.split()

        return None

if __name__ == "__main__":
    crawler = EfapelCrawler()
    extractor = EfapelExtractor()
    pipeline = EfapelPipeline(crawler, extractor)
    result = pipeline.run()

    print("\n=== PIPELINE RESULT ===")
    print(result)



