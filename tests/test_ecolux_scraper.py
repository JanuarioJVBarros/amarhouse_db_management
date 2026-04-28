from pathlib import Path
from types import SimpleNamespace

from scrapers.ecolux.crawler import EcoluxCrawler
from scrapers.ecolux.extractor import EcoluxExtractor
from scrapers.ecolux.parser import EcoluxParser
from scrapers.ecolux.run_pipeline import EcoluxPipeline
from scrapers.ecolux.urls import PRODUCTS_URL


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def load_fixture(name):
    return (FIXTURES_DIR / name).read_text(encoding="utf-8")


class DummyResponse:
    def __init__(self, text):
        self.text = text

    def raise_for_status(self):
        return None


class DummySession:
    def __init__(self, pages):
        self.pages = pages
        self.calls = []
        self.headers = {}
        self.cookies = DummyCookies()

    def get(self, url, timeout=30):
        self.calls.append((url, timeout))
        return DummyResponse(self.pages[url])


class DummyCookies:
    def __init__(self):
        self.values = []

    def set(self, name, value, domain=None, path=None):
        self.values.append((name, value, domain, path))


class StubPublisher:
    def __init__(self):
        self.published = []

    def publish(self, product):
        self.published.append(product)
        return {"product_id": product.slug, "status": "published"}


class CapturingPublisher:
    def __init__(self, client):
        self.client = client
        self.published = []

    def publish(self, product):
        self.published.append(product)
        return {"product_id": product.slug, "status": "published"}


def test_ecolux_crawler_extracts_category_and_product_links():
    session = DummySession(
        {
            PRODUCTS_URL: load_fixture("ecolux_catalog.html"),
            "https://ecolux-lighting.com/categoria_producto/bombilleria/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/categoria_producto/paneles/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/productos-ecolux-lighting/ventilacion-led/": load_fixture("ecolux_category.html"),
        }
    )
    crawler = EcoluxCrawler(session=session)

    category_links = crawler.get_category_links(PRODUCTS_URL)
    product_links = crawler.crawl_category(PRODUCTS_URL)

    assert category_links == [
        "https://ecolux-lighting.com/categoria_producto/bombilleria/",
        "https://ecolux-lighting.com/categoria_producto/paneles/",
        "https://ecolux-lighting.com/productos-ecolux-lighting/ventilacion-led/",
    ]
    assert product_links == [
        "https://ecolux-lighting.com/productos/luxe/",
        "https://ecolux-lighting.com/productos/polar-e27-5w-9w/",
    ]
    assert session.headers["Accept-Language"].startswith("pt-PT")
    assert ("googtrans", "/es/pt", None, None) in session.cookies.values
    assert ("googtrans", "/es/pt", None, "/") in session.cookies.values
    assert ("gt_auto_switch", "1", None, "/") in session.cookies.values


def test_ecolux_extractor_builds_product_with_option_groups_and_variants():
    extractor = EcoluxExtractor()
    product = extractor.extract(
        load_fixture("ecolux_product.html"),
        "https://ecolux-lighting.com/productos/polar-e27-5w-9w/",
    )

    assert product.name == "POLAR E27 5W/9W"
    assert product.slug == "polar-e27-5w-9w"
    assert product.supplier == "ecolux"
    assert product.description == "Lâmpada POLAR E27"
    assert product.labels == ["Lâmpadas", "POLAR E27 5W/9W"]
    assert product.images == ["https://ecolux-lighting.com/wp-content/uploads/2025/05/polar-main.jpg"]
    assert product.option_groups == [
        {"name": "Potência (W)", "options": ["5", "9"]},
        {"name": "Temperatura (K)", "options": ["3.000K", "4.200K"]},
    ]
    assert product.variants == [
        {
            "name": "POLAR E27 5W/9W 3.000K",
            "sku": "EC-2125",
            "price": 0,
            "options": {"Potência (W)": "9", "Temperatura (K)": "3.000K"},
        },
        {
            "name": "POLAR E27 5W/9W 4.200K",
            "sku": "EC-2126",
            "price": 0,
            "options": {"Potência (W)": "9", "Temperatura (K)": "4.200K"},
        },
        {
            "name": "POLAR E27 5W/9W 3.000K",
            "sku": "EC-2134",
            "price": 0,
            "options": {"Potência (W)": "5", "Temperatura (K)": "3.000K"},
        },
    ]


def test_ecolux_pipeline_can_publish_missing_products(tmp_path):
    session = DummySession(
        {
            PRODUCTS_URL: load_fixture("ecolux_catalog.html"),
            "https://ecolux-lighting.com/categoria_producto/bombilleria/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/categoria_producto/paneles/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/productos-ecolux-lighting/ventilacion-led/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/productos/polar-e27-5w-9w/": load_fixture("ecolux_product.html"),
            "https://ecolux-lighting.com/productos/luxe/": load_fixture("ecolux_product.html"),
        }
    )
    crawler = EcoluxCrawler(session=session)
    extractor = EcoluxExtractor()
    publisher = StubPublisher()
    pipeline = EcoluxPipeline(crawler=crawler, extractor=extractor, publisher=publisher)

    result = pipeline.run_and_publish_missing(
        start_urls=[PRODUCTS_URL],
        output_file=tmp_path / "ecolux.json",
    )

    assert result["scraped"] == 2
    assert result["published"] == 2
    assert len(publisher.published) == 2


def test_ecolux_pipeline_dry_run_skips_real_publish(tmp_path):
    session = DummySession(
        {
            PRODUCTS_URL: load_fixture("ecolux_catalog.html"),
            "https://ecolux-lighting.com/categoria_producto/bombilleria/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/categoria_producto/paneles/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/productos-ecolux-lighting/ventilacion-led/": load_fixture("ecolux_category.html"),
            "https://ecolux-lighting.com/productos/polar-e27-5w-9w/": load_fixture("ecolux_product.html"),
            "https://ecolux-lighting.com/productos/luxe/": load_fixture("ecolux_product.html"),
        }
    )
    crawler = EcoluxCrawler(session=session)
    extractor = EcoluxExtractor()
    publisher = StubPublisher()
    pipeline = EcoluxPipeline(crawler=crawler, extractor=extractor, publisher=publisher)

    result = pipeline.run_and_publish_missing(
        start_urls=[PRODUCTS_URL],
        output_file=tmp_path / "ecolux.json",
        dry_run=True,
    )

    assert result["scraped"] == 2
    assert result["published"] == 2
    assert result["dry_run"] is True
    assert publisher.published == []
    assert result["results"][0]["status"] == "dry-run"


def test_ecolux_pipeline_loads_environment_before_creating_beevo_client(monkeypatch):
    extractor = EcoluxExtractor()
    product = extractor.extract(
        load_fixture("ecolux_product.html"),
        "https://ecolux-lighting.com/productos/polar-e27-5w-9w/",
    )
    created_publishers = []

    monkeypatch.setattr(
        "scrapers.ecolux.run_pipeline.load_environment",
        lambda: SimpleNamespace(
            beevo_url="https://example.test/admin-api",
            beevo_cookie="session=value",
            request_timeout=45,
        ),
    )

    def build_publisher(client):
        publisher = CapturingPublisher(client)
        created_publishers.append(publisher)
        return publisher

    monkeypatch.setattr("scrapers.ecolux.run_pipeline.ProductPublisher", build_publisher)

    pipeline = EcoluxPipeline(publisher=None)
    result = pipeline.publish_missing([product], dry_run=False)

    assert result == [{"product_id": "polar-e27-5w-9w", "status": "published"}]
    assert len(created_publishers) == 1
    assert created_publishers[0].client.base_url == "https://example.test/admin-api"
    assert created_publishers[0].client.beevo_cookie == "session=value"
    assert created_publishers[0].client.timeout == 45
    assert created_publishers[0].published == [product]


def test_ecolux_extractor_builds_all_variants_from_table_driven_product():
    html = """
    <html>
      <body>
        <ul class="breadcrumb">
          <li><a href="/">Inicio</a></li>
          <li><a href="/productos-ecolux-lighting/">Productos</a></li>
          <li><a href="/categoria_producto/tubos-led/">Tubos Led</a></li>
          <li>TUBOS FENIX</li>
        </ul>

        <h2>TUBOS FENIX</h2>
        <p>Ya esta aqui el tubo de iluminacion led Fenix.</p>

        <h2>DATOS TECNICOS</h2>
        <h3>Tonic 9W / 18W / 22W</h3>
        <table>
          <tr>
            <th>Ref</th>
            <th>W</th>
            <th>Voltaje</th>
            <th>Temp (K)</th>
            <th>Lm</th>
            <th>Dim</th>
          </tr>
          <tr><td>EC-2647</td><td>9</td><td>175-265V</td><td>3.000</td><td>900</td><td>-</td></tr>
          <tr><td>EC-2648</td><td>9</td><td>175-265V</td><td>4.000</td><td>900</td><td>-</td></tr>
          <tr><td>EC-2649</td><td>9</td><td>175-265V</td><td>6.000</td><td>900</td><td>-</td></tr>
          <tr><td>EC-2650</td><td>18</td><td>175-265V</td><td>3.000</td><td>1.800</td><td>-</td></tr>
          <tr><td>EC-2651</td><td>18</td><td>175-265V</td><td>4.000</td><td>1.800</td><td>-</td></tr>
          <tr><td>EC-2652</td><td>18</td><td>175-265V</td><td>6.000</td><td>1.800</td><td>-</td></tr>
          <tr><td>EC-2653</td><td>22</td><td>175-265V</td><td>3.000</td><td>2.200</td><td>-</td></tr>
          <tr><td>EC-2654</td><td>22</td><td>175-265V</td><td>4.000</td><td>2.200</td><td>-</td></tr>
          <tr><td>EC-2655</td><td>22</td><td>175-265V</td><td>6.000</td><td>2.200</td><td>-</td></tr>
        </table>
      </body>
    </html>
    """

    extractor = EcoluxExtractor()
    product = extractor.extract(
        html,
        "https://ecolux-lighting.com/productos/tubos-fenix/",
    )

    assert product.name == "TUBOS FENIX"
    assert product.option_groups == [
        {"name": "Potência (W)", "options": ["9", "18", "22"]},
        {"name": "Temperatura (K)", "options": ["3.000", "4.000", "6.000"]},
    ]
    assert len(product.variants) == 9
    assert product.variants[0] == {
        "name": "TUBOS FENIX 9 3.000",
        "sku": "EC-2647",
        "price": 0,
        "options": {"Potência (W)": "9", "Temperatura (K)": "3.000"},
    }
    assert product.variants[-1] == {
        "name": "TUBOS FENIX 22 6.000",
        "sku": "EC-2655",
        "price": 0,
        "options": {"Potência (W)": "22", "Temperatura (K)": "6.000"},
    }


def test_ecolux_extractor_builds_variants_from_alba_text_rows():
    html = """
    <html>
      <body>
        <ul class="breadcrumb">
          <li><a href="/">Inicio</a></li>
          <li><a href="/categoria_producto/bombilleria/">Bombillería</a></li>
          <li><a href="/categoria_producto/led-bulbs/">Led Bulbs</a></li>
          <li>ALBA E14 7W</li>
        </ul>

        <h2>ALBA E14 7W</h2>
        <img src="/images/alba-main.jpg" alt="ALBA 7W" />
        <h2>DATOS TÉCNICOS</h2>
        <div>ALBA 7W</div>
        <div>Ref W Base Voltaje Temp (K) Lm Dim</div>
        <div>EC-3337 7 E14 220-240V 3.000 575 -</div>
        <div>EC-3338 7 E14 220-240V 4.200 585 -</div>
        <div>EC-3339 7 E14 220-240V 6.000 600 -</div>
      </body>
    </html>
    """

    extractor = EcoluxExtractor()
    product = extractor.extract(
        html,
        "https://ecolux-lighting.com/productos/alba-7w-e14/",
    )

    assert product.name == "ALBA E14 7W"
    assert product.sku == "EC-3337"
    assert product.images == ["https://ecolux-lighting.com/images/alba-main.jpg"]
    assert product.option_groups == [
        {"name": "Temperatura (K)", "options": ["3.000", "4.200", "6.000"]},
    ]
    assert product.variants == [
        {
            "name": "ALBA E14 7W 3.000",
            "sku": "EC-3337",
            "price": 0,
            "options": {"Temperatura (K)": "3.000"},
        },
        {
            "name": "ALBA E14 7W 4.200",
            "sku": "EC-3338",
            "price": 0,
            "options": {"Temperatura (K)": "4.200"},
        },
        {
            "name": "ALBA E14 7W 6.000",
            "sku": "EC-3339",
            "price": 0,
            "options": {"Temperatura (K)": "6.000"},
        },
    ]


def test_ecolux_extractor_uses_section_as_option_when_rows_would_duplicate():
    html = """
    <html>
      <body>
        <ul class="breadcrumb">
          <li><a href="/">Inicio</a></li>
          <li><a href="/categoria_producto/downlights/">Downlights</a></li>
          <li>DOWNLIGHT BRAVA 9W / 12W / 18W / CCT</li>
        </ul>

        <h2>DOWNLIGHT BRAVA 9W / 12W / 18W / CCT</h2>
        <h2>DATOS TÉCNICOS</h2>
        <h3>BRAVA REDONDO</h3>
        <div>Ref W Acabado Voltaje Temp (K) Lm Dim</div>
        <div>EC-4567 18 Blanco/White 100-265V CCT 100 -</div>
        <h3>BRAVA CUADRADO</h3>
        <div>Ref W Acabado Voltaje Temp (K) Lm Dim</div>
        <div>EC-4568 18 Blanco/White 100-265V CCT 100 -</div>
      </body>
    </html>
    """

    extractor = EcoluxExtractor()
    product = extractor.extract(
        html,
        "https://ecolux-lighting.com/productos/downlight-brava-9w-12w-18w-cct/",
    )

    assert product.option_groups == [
        {"name": "Modelo", "options": ["BRAVA QUADRADO", "BRAVA REDONDO"]},
    ]
    assert product.variants == [
        {
            "name": "DOWNLIGHT BRAVA 9W / 12W / 18W / CCT BRAVA REDONDO",
            "sku": "EC-4567",
            "price": 0,
            "options": {"Modelo": "BRAVA REDONDO"},
        },
        {
            "name": "DOWNLIGHT BRAVA 9W / 12W / 18W / CCT BRAVA QUADRADO",
            "sku": "EC-4568",
            "price": 0,
            "options": {"Modelo": "BRAVA QUADRADO"},
        },
    ]


def test_ecolux_parser_extracts_rows_from_non_ideal_table_markup():
    html = """
    <html>
      <body>
        <h2>DATOS TECNICOS</h2>
        <h3>TUBOS FENIX</h3>
        <table>
          <tr><td><img src="/wp-content/uploads/example.jpg" /></td></tr>
          <tr>
            <td>Ref.</td>
            <td>W</td>
            <td>Voltaje</td>
            <td>Temp (K)</td>
            <td>Lm</td>
            <td>Dim</td>
          </tr>
          <tr>
            <th>EC-2647</th>
            <td>9</td>
            <td>175-265V</td>
            <td>3.000</td>
            <td>900</td>
            <td>-</td>
          </tr>
          <tr>
            <th>EC-2648</th>
            <td>9</td>
            <td>175-265V</td>
            <td>4.000</td>
            <td>900</td>
            <td>-</td>
          </tr>
        </table>
      </body>
    </html>
    """

    parser = EcoluxParser(html)
    sections = parser.technical_sections()

    assert sections == [
        {
            "section": "TUBOS FENIX",
            "rows": [
                {
                    "Ref": "EC-2647",
                    "W": "9",
                    "Voltaje": "175-265V",
                    "Temp (K)": "3.000",
                    "Lm": "900",
                    "Dim": "-",
                },
                {
                    "Ref": "EC-2648",
                    "W": "9",
                    "Voltaje": "175-265V",
                    "Temp (K)": "4.000",
                    "Lm": "900",
                    "Dim": "-",
                },
            ],
        }
    ]


def test_ecolux_extractor_splits_text_catalog_sections_into_multiple_products():
    html = """
    <html>
      <body>
        <ul class="breadcrumb">
          <li><a href="/">Inicio</a></li>
          <li><a href="/categoria_producto/focos-de-carril/">Focos de Carril</a></li>
          <li><a href="/categoria_producto/estandar/">Estándar</a></li>
          <li>Accesorios de carril estándar</li>
        </ul>

        <h2>ACCESORIOS DE CARRIL ESTÁNDAR</h2>
        <h2>SUPERFICIE</h2>
        <div>Ref Descripción Acabado</div>
        <img src="/images/surface-1m.jpg" alt="Accesorio focos de carril EC-4250 EC-4251" />
        <div>EC-4250 Carril de aluminio trifásico 1 metro Blanco/White</div>
        <div>EC-4251 Carril de aluminio trifásico de 1 metro Negro/Black</div>
        <img src="/images/surface-2m.jpg" alt="Accesorio focos de carril EC-4252 EC-4253" />
        <div>EC-4252 Carril de aluminio trifásico de 2 metro Blanco/White</div>
        <div>EC-4253 Carril de aluminio trifásico de 2 metro Negro/Black</div>

        <h2>EMPOTRABLES</h2>
        <div>Ref Descripción Acabado</div>
        <img src="/images/recessed-1m.jpg" alt="Accesorio focos de carril EC-4274 EC-4275" />
        <div>EC-4274 Carril empotrado de aluminio trifásico de 1 metro Blanco/White</div>
        <div>EC-4275 Carril empotrado de aluminio trifásico de 1 metro Negro/Black</div>
        <img src="/images/clamp.jpg" alt="EC-4296" />
        <div>EC-4296 Garra de sujección de carril -</div>
      </body>
    </html>
    """

    extractor = EcoluxExtractor()
    products = extractor.extract(
        html,
        "https://ecolux-lighting.com/productos/accesorios-focos-de-carril/",
    )

    assert len(products) == 4

    first_product = products[0]
    assert first_product.name == "Carril de alumínio trifásico 1 metro"
    assert first_product.sku == "EC-4250"
    assert first_product.images == ["https://ecolux-lighting.com/images/surface-1m.jpg"]
    assert first_product.option_groups == [
        {"name": "Acabamento", "options": ["Branco", "Preto"]},
    ]
    assert first_product.variants[0] == {
        "name": "Carril de alumínio trifásico 1 metro Branco",
        "sku": "EC-4250",
        "price": 0,
        "options": {"Acabamento": "Branco"},
    }

    last_product = products[-1]
    assert last_product.name == "Garra de fixação de carril"
    assert last_product.sku == "EC-4296"
    assert last_product.images == ["https://ecolux-lighting.com/images/clamp.jpg"]
    assert last_product.option_groups == []
    assert last_product.variants == [
        {
            "name": "Garra de fixação de carril",
            "sku": "EC-4296",
            "price": 0,
            "options": {},
        }
    ]
