from dataclasses import dataclass, field
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

    images: List[str] = field(default_factory=list)
    labels: List[str] = field(default_factory=list)
    option_groups: List[Dict[str, Any]] = field(default_factory=list)
    facet_value_ids: List[str] = field(default_factory=list)

    colors: Optional[str] = None
    variants: List[Dict[str, Any]] = field(default_factory=list)

    source_url: Optional[str] = None
    supplier: Optional[str] = None
