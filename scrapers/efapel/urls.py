BASE_URL = "https://www.efapel.pt/pt"

START_CATEGORY_URL = f"{BASE_URL}/produtos"

#CATEGORY_LIST = ["logus-90", "estanque-48", "burotica"]
CATEGORY_LIST = ["jazz"]

PRODUCT_URL_PREFIX = "/products/"

def is_product_url(url: str) -> bool:
    return PRODUCT_URL_PREFIX in url and len(url.split("/")) > 4

def normalize_url(url: str) -> str:
    if url.startswith("http"):
        return url
    return BASE_URL + url