from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

@dataclass
class ProductOption:
    code: str
    name: str

@dataclass
class OptionGroup:
    code: str
    name: str
    options: List[ProductOption] = field(default_factory=list)

@dataclass
class ProductVariant:
    sku: str
    price: float
    stock: int
    option_codes: List[str]  # e.g. ["2000k"]

@dataclass
class ProductImage:
    path: str  # local path OR URL (we’ll support local first)
    is_featured: bool = False

@dataclass
class Product:
    # identity
    name: str
    slug: str

    # content
    description: str = ""
    description_2: str = ""
    other_information: str = ""

    # structure
    enabled: bool = True

    # relations
    option_groups: List[OptionGroup] = field(default_factory=list)
    variants: List[ProductVariant] = field(default_factory=list)
    images: List[ProductImage] = field(default_factory=list)

    # labels (facet values)
    facet_value_ids: List[str] = field(default_factory=list)

    # optional CMS fields
    featured: bool = False
    main_collection_id: Optional[str] = None
    related_products_ids: List[str] = field(default_factory=list)
    google_id_id: Optional[str] = None

    # metadata (for scraping/debugging)
    source: Dict[str, Any] = field(default_factory=dict)