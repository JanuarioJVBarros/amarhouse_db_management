from scrapers.aronlight.crawler import AronlightCrawler
from scrapers.aronlight.extractor import AronlightExtractor
from scrapers.aronlight.parser import AronlightParser


CATEGORY_PAGE_1 = """
<html>
  <body>
    <a href="/en/project-details/luminaria-encastrar-ace/">ACE</a>
    <a href="/project-details/luminaria-encastrar-hale/">HALE</a>
    <a href="/portfolio/downlights-led/page/2/">2</a>
  </body>
</html>
"""


CATEGORY_PAGE_2 = """
<html>
  <body>
    <a href="/en/project-details/slit/">Slit</a>
  </body>
</html>
"""


ACE_PRODUCT_HTML = """
<html>
  <body>
    <ul class="breadcrumb">
      <li><a href="/en/">Home</a></li>
      <li><a href="/en/architectural">Architectural &amp; Design</a></li>
    </ul>
    <h1>ACE</h1>
    <img src="/wp-content/uploads/ace-main.jpg" alt="ACE main" />
    <img src="/wp-content/uploads/ace-detail.jpg" alt="ACE detail" />
    <h4>ACE</h4>
    <p>Recessed, high efficiency luminaire.</p>
    <div class="wpb_wrapper">
      <p>Summary block.</p>
      <div class="table-responsive">
        <table>
          <thead><tr><th>Specifications</th></tr></thead>
          <tbody>
            <tr><td>IP</td><td>44</td></tr>
          </tbody>
        </table>
      </div>
    </div>
    <h5>10 WATTS</h5>
    <table>
      <tr><td>CCT</td><td>2700K</td><td>4000K</td></tr>
      <tr><td>LUMENS</td><td>850 Lm</td><td>850 Lm</td></tr>
      <tr><td>SIZE</td><td>90x90x76mm</td><td>90x90x76mm</td></tr>
      <tr><td>CUTOUT</td><td>84x84mm</td><td>84x84mm</td></tr>
      <tr><td>COLOR</td><td>White</td><td>White</td></tr>
      <tr><td>SKU</td><td>ILAR-00662</td><td>ILAR-00663</td></tr>
    </table>
  </body>
</html>
"""


LINEAR_PRODUCT_HTML = """
<html>
  <body>
    <h1>Linear Modular Light</h1>
    <img src="/wp-content/uploads/linear-main.jpg" alt="Linear main" />
    <h4>Linear Modular Light</h4>
    <p>Modular aluminum luminaire with an elegant design.</p>
    <h5>20 WATTS</h5>
    <table>
      <tr><td>COLOR TEMPERATURE</td><td>3CCT (3000K-4000K-6000K)</td></tr>
      <tr><td>TOTAL LUMINOUS FLUX</td><td>2400lm</td></tr>
      <tr><td>SIZE</td><td>600x54x58mm</td></tr>
      <tr><td>COLOR</td><td>Black</td></tr>
      <tr><td>SKU</td><td>ILAR-02111</td></tr>
    </table>
    <h5>40 WATTS</h5>
    <table>
      <tr><td>COLOR TEMPERATURE</td><td>3CCT (3000K-4000K-6000K)</td></tr>
      <tr><td>TOTAL LUMINOUS FLUX</td><td>4800lm</td></tr>
      <tr><td>SIZE</td><td>1200x54x58mm</td></tr>
      <tr><td>COLOR</td><td>Black</td></tr>
      <tr><td>SKU</td><td>ILAR-02112</td></tr>
    </table>
    <h5>ACCESSORIES</h5>
    <table>
      <tr><td>Accessories</td><td>SKU</td></tr>
      <tr><td>L Conector</td><td>ILAR-02113</td></tr>
    </table>
  </body>
</html>
"""


TABBED_PRODUCT_HTML = """
<html>
  <body>
    <h1>Module Dimmable</h1>
    <h4>Module Dimmable</h4>
    <p>Spotlight module with dimmable driver.</p>
    <div class="rt_tabs clearfix tab-position-1 style-4">
      <ul class="tab_nav hidden-xs">
        <li class="tab_title active" id="tab-1-title" data-tab-number="1">6 WATTS</li>
      </ul>
      <div class="tab_contents">
        <div class="tab_content_wrapper animation active" id="tab-1" data-tab-content="1">
          <div id="tab-1-inline-title" class="tab_title visible-xs" data-tab-number="1">6 WATTS</div>
          <div class="tab_content">
            <div class="table-responsive">
              <table class="easy-table easy-table-default">
                <thead>
                  <tr>
                    <th>CCT</th>
                    <th>3000K-4000K-6000K</th>
                  </tr>
                </thead>
                <tbody>
                  <tr><td>LUMENS</td><td>550 Lm</td></tr>
                  <tr><td>SIZE</td><td>Ø50x23mm</td></tr>
                  <tr><td>SKU</td><td>ILAR-03567</td></tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  </body>
</html>
"""


class StubSession:
    def __init__(self, responses):
        self.responses = responses

    def get(self, url, timeout=30):
        class Response:
            def __init__(self, text):
                self.text = text

            def raise_for_status(self):
                return None

        return Response(self.responses[url])


def test_aronlight_crawler_collects_product_links_across_pagination():
    session = StubSession(
        {
            "https://aronlight.com/portfolio/downlights-led/": CATEGORY_PAGE_1,
            "https://aronlight.com/portfolio/downlights-led/page/2/": CATEGORY_PAGE_2,
        }
    )
    crawler = AronlightCrawler(session=session)

    result = crawler.crawl_category("https://aronlight.com/portfolio/downlights-led/")

    assert result == [
        "https://aronlight.com/project-details/luminaria-encastrar-ace/",
        "https://aronlight.com/project-details/luminaria-encastrar-hale/",
        "https://aronlight.com/project-details/slit/",
    ]


def test_aronlight_parser_extracts_title_description_images_and_tables():
    parser = AronlightParser(ACE_PRODUCT_HTML)

    assert parser.page_title() == "ACE"
    assert parser.description() == "Summary block."
    assert "Summary block." in parser.description_full()
    assert parser.breadcrumb_labels() == ["Architectural & Design"]
    assert parser.images("https://aronlight.com/en/project-details/luminaria-encastrar-ace/") == [
        "https://aronlight.com/wp-content/uploads/ace-main.jpg",
        "https://aronlight.com/wp-content/uploads/ace-detail.jpg",
    ]
    assert parser.product_tables()[0]["section"] == "10 WATTS"


def test_aronlight_extractor_builds_variant_matrix_product():
    extractor = AronlightExtractor()

    product = extractor.extract(
        ACE_PRODUCT_HTML,
        "https://aronlight.com/en/project-details/luminaria-encastrar-ace/",
    )

    assert product.name == "ACE"
    assert product.supplier == "aronlight"
    assert product.sku == "ILAR-00662"
    assert product.description == "Summary block."
    assert "Summary block." in product.description_full
    assert product.facet_value_ids == ["164"]
    assert product.option_groups == [{"name": "Cct", "options": ["2700K", "4000K"]}]
    assert product.variants == [
        {
            "name": "ACE 2700K",
            "sku": "ILAR-00662",
            "price": 0,
            "options": {"Cct": "2700K"},
        },
        {
            "name": "ACE 4000K",
            "sku": "ILAR-00663",
            "price": 0,
            "options": {"Cct": "4000K"},
        },
    ]


def test_aronlight_extractor_builds_multi_section_variants_and_skips_accessories():
    extractor = AronlightExtractor()

    product = extractor.extract(
        LINEAR_PRODUCT_HTML,
        "https://aronlight.com/en/project-details/linear-modular-light/",
    )

    assert product.sku == "ILAR-02111"
    assert product.option_groups == [{"name": "Power", "options": ["20 WATTS", "40 WATTS"]}]
    assert product.variants == [
        {
            "name": "Linear Modular Light 20 WATTS",
            "sku": "ILAR-02111",
            "price": 0,
            "options": {"Power": "20 WATTS"},
        },
        {
            "name": "Linear Modular Light 40 WATTS",
            "sku": "ILAR-02112",
            "price": 0,
            "options": {"Power": "40 WATTS"},
        },
    ]


def test_aronlight_extractor_uses_tab_titles_as_variant_sections():
    extractor = AronlightExtractor()

    product = extractor.extract(
        TABBED_PRODUCT_HTML,
        "https://aronlight.com/project-details/module-dimmable/",
    )

    assert product.sku == "ILAR-03567"
    assert product.option_groups == []
    assert product.variants == [
        {
            "name": "Module Dimmable 6 WATTS",
            "sku": "ILAR-03567",
            "price": 0,
            "options": {},
        }
    ]
