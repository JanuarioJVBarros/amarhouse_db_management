from scrapers.aronlight.find_sku_references import analyze_page, crawl_for_sku_references


HTML = """
<html>
  <body>
    <h1>Dimmable Driver</h1>
    <p>Control gear for downlights.</p>
    <a href="/fichas-tecnicas/drivers/ILAR-01013-driver.pdf">Data Sheet</a>
    <a href="/project-details/driver-family/">Driver Family</a>
    <div>Alternative SKU ILDV-00044</div>
  </body>
</html>
"""


class StubCrawler:
    def __init__(self, responses):
        self.responses = responses

    def fetch(self, url):
        return self.responses[url]


def test_analyze_page_detects_page_and_link_sku_references():
    matches, next_links = analyze_page(
        "https://aronlight.com/project-details/test-driver/",
        HTML,
        ["ILAR-01013", "ILDV-00044"],
    )

    assert set(matches) == {"ILAR-01013", "ILDV-00044"}
    assert any(entry["match_type"] == "link_reference" for entry in matches["ILAR-01013"])
    assert any(entry["match_type"] == "page_text" for entry in matches["ILDV-00044"])
    assert next_links == ["https://aronlight.com/project-details/driver-family/"]


def test_crawl_for_sku_references_collects_matches_across_pages():
    crawler = StubCrawler(
        {
            "https://aronlight.com/portfolio/drivers-power-en/": HTML,
            "https://aronlight.com/project-details/driver-family/": "<html><body><p>ILAR-02952</p></body></html>",
        }
    )

    result = crawl_for_sku_references(
        ["https://aronlight.com/portfolio/drivers-power-en/"],
        ["ILAR-01013", "ILAR-02952", "ILAR-99999"],
        crawler=crawler,
        max_pages=10,
    )

    assert sorted(result["matches"]) == ["ILAR-01013", "ILAR-02952"]
    assert result["missing_skus"] == ["ILAR-99999"]
