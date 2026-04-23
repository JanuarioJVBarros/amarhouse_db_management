from dataclasses import dataclass
from typing import List, Optional, Dict, Any


@dataclass
class ScrapedProduct:
    name: Optional[str] = None
    slug: Optional[str] = None

    description: Optional[str] = None
    description_full: Optional[str] = None

    price: Optional[str] = None
    reference: Optional[str] = None
    sku: Optional[str] = None

    images: List[str] = None
    labels: List[str] = None

    colors: Optional[str] = None
    variants: List[Dict[str, Any]] = None

    source_url: Optional[str] = None