BASE_URL = "https://www.golmar.es"

START_CATEGORY_URL = f"{BASE_URL}/products"
START_URLS = [START_CATEGORY_URL]

PRODUCT_URL_PREFIX = "/products/"

def is_product_url(url: str) -> bool:
    return PRODUCT_URL_PREFIX in url and len(url.split("/")) > 4


def normalize_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE_URL + url
