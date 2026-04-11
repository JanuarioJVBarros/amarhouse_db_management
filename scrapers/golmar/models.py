from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ScrapedProduct:
    name: str
    slug: str
    description: str = ""
    description_full: str = ""
    price: Optional[str] = None
    reference: Optional[str] = None
    sku: Optional[str] = None

    images: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)

    source_url: str = ""