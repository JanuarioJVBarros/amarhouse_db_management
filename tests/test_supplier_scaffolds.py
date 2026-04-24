from scrapers.base.pipeline import SupplierPipeline
from scrapers.ecolux.run_pipeline import EcoluxPipeline
from scrapers.golmar.run_pipeline import GolmarPipeline
from scrapers.ledme.run_pipeline import LedmePipeline
from scrapers.rointe.run_pipeline import RointePipeline


class DummyCrawler:
    def __init__(self):
        self.urls = []

    def crawl_category(self, start_url):
        self.urls.append(start_url)
        return []

    def fetch(self, url):
        raise AssertionError("fetch should not be called when crawl_category returns no URLs")


class DummyExtractor:
    def extract(self, html, url):
        raise AssertionError("extract should not be called when crawl_category returns no URLs")


def test_supplier_scaffold_pipelines_extend_shared_pipeline():
    for pipeline in [
        GolmarPipeline(crawler=DummyCrawler(), extractor=DummyExtractor()),
        EcoluxPipeline(crawler=DummyCrawler(), extractor=DummyExtractor()),
        LedmePipeline(crawler=DummyCrawler(), extractor=DummyExtractor()),
        RointePipeline(crawler=DummyCrawler(), extractor=DummyExtractor()),
    ]:
        assert isinstance(pipeline, SupplierPipeline)


def test_supplier_scaffold_pipelines_can_run_with_injected_dependencies(tmp_path):
    pipeline = GolmarPipeline(crawler=DummyCrawler(), extractor=DummyExtractor())

    products = pipeline.run(
        ["https://example.test/category"],
        output_file=tmp_path / "test_output.json",
    )

    assert products == []
