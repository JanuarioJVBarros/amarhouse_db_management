from abc import ABC, abstractmethod


class BaseProductExtractor(ABC):
    @abstractmethod
    def extract(self, html, url):
        raise NotImplementedError
