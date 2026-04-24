from pathlib import Path

from scrapers.efapel.extractor import EfapelExtractor
from scrapers.efapel.parser import EfapelParser
from scrapers.golmar.extractor import GolmarExtractor
from scrapers.golmar.parser import GolmarParser


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


def test_golmar_parser_reads_text_html_links_and_images():
    html = load_fixture("golmar_product.html")
    parser = GolmarParser(html)

    assert parser.text("h1") == "Wall Intercom Kit"
    assert "Two-wire system" in parser.html(".product-info ul")
    assert parser.images() == [
        "https://www.golmar.es/media/product-a.jpg",
        "https://www.golmar.es/media/product-b.jpg",
    ]

    links = parser.all_links()
    assert "https://www.golmar.es/products/intercom-en" in links
    assert "https://www.golmar.es/support/manuals" in links


def test_golmar_extractor_builds_expected_scraped_product():
    html = load_fixture("golmar_product.html")
    extractor = GolmarExtractor()

    product = extractor.extract(
        html,
        "https://www.golmar.es/products/intercom-en/wall-intercom-kit",
    )

    assert product.name == "Wall Intercom Kit"
    assert product.slug == "wall-intercom-kit"
    assert "Surface mounted" in product.description
    assert "Detailed installation information" in product.description_full
    assert product.price == "199.99€"
    assert product.reference == "REF-900"
    assert product.sku == "SKU-900"
    assert product.labels == ["Indoor", "Intercom"]
    assert product.images == [
        "https://www.golmar.es/media/product-a.jpg",
        "https://www.golmar.es/media/product-b.jpg",
    ]


def test_efapel_parser_selects_and_reads_html():
    html = load_fixture("efapel_category.html")
    parser = EfapelParser(html)

    rows = parser.select("tr.row")
    assert len(rows) == 1
    assert parser.text("h4") == "Decorative Frame"
    assert "FRAME01" in parser.html(".ref")


def test_efapel_extractor_builds_products_with_color_variants():
    html = load_fixture("efapel_category.html")
    extractor = EfapelExtractor()

    products = extractor.extract(
        html,
        "https://www.efapel.pt/produtos/decorative-frames",
    )

    assert len(products) == 2

    colored = products[0]
    assert colored.name == "Decorative Frame"
    assert colored.slug == "decorative-frame"
    assert colored.labels == ["127"]
    assert colored.images == ["https://www.efapel.pt/images/frame-white.jpg"]
    assert colored.option_groups == [{"name": "Cor", "options": ["BR", "PT"]}]
    assert colored.variants == [
        {"name": "Decorative Frame - BR", "price": 0, "sku": "FRAME01BR", "option": "BR"},
        {"name": "Decorative Frame - PT", "price": 0, "sku": "FRAME01PT", "option": "PT"},
    ]
    assert colored.supplier == "efapel"

    neutral = products[1]
    assert neutral.name == "Standard Frame"
    assert neutral.variants == [
        {"name": "Standard Frame", "price": 0, "sku": "FRAME02", "option": None}
    ]
