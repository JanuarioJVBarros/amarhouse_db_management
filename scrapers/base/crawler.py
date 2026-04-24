from abc import ABC, abstractmethod

import requests


class BaseCatalogCrawler(ABC):
    def __init__(self, base_url, timeout=30, session=None):
        self.base_url = base_url
        self.timeout = timeout
        self.session = session or requests.Session()

    def fetch(self, url):
        response = self.session.get(url, timeout=self.timeout)
        response.raise_for_status()
        return response.text

    @abstractmethod
    def crawl_category(self, start_url):
        raise NotImplementedError
