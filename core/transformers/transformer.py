import re
from typing import Dict, Any, List
from core.models import Product, OptionGroup, ProductOption, ProductVariant, ProductImage
from utils.helpers import slugify

class ProductTransformer:
    def __init__(self, language_code):
        self.language_code = language_code

    def transform(self, data: Dict[str, Any]) -> Product:
        """
        Convert scraped website data → internal Product model
        """

        # -------------------------
        # 1. BASIC INFO
        # -------------------------
        name = data.get("title", "").strip()
        slug = slugify(name)

        description = data.get("description_html", "")
        description_2 = data.get("full_description_html", "")
        other_information = data.get("other_information", "")

        # -------------------------
        # 2. IMAGES
        # -------------------------
        images = [
            ProductImage(
                path=img,
                is_featured=(i == 0)
            )
            for i, img in enumerate(data.get("images", []))
        ]

        # -------------------------
        # 3. OPTION GROUPS
        # -------------------------
        option_groups: List[OptionGroup] = []

        attributes = data.get("attributes", {})

        for attr_code, values in attributes.items():
            options = [
                ProductOption(
                    code=self._normalize_option_code(v),
                    name=v
                )
                for v in values
            ]

            option_groups.append(
                OptionGroup(
                    code=attr_code,
                    name=self._pretty_name(attr_code),
                    options=options
                )
            )

        # -------------------------
        # 4. VARIANTS
        # -------------------------
        variants = self._build_variants(data)

        # -------------------------
        # 5. LABELS (FACET VALUES)
        # -------------------------
        facet_value_ids = data.get("facet_value_ids", [])

        # -------------------------
        # 6. BUILD PRODUCT
        # -------------------------
        return Product(
            name=name,
            slug=slug,
            description=description,
            description_2=description_2,
            other_information=other_information,
            enabled=True,

            option_groups=option_groups,
            variants=variants,
            images=images,

            facet_value_ids=facet_value_ids,

            source={
                "url": data.get("url"),
                "raw": data
            }
        )

    # -------------------------
    # VARIANT BUILDER
    # -------------------------

    def _build_variants(self, data: Dict[str, Any]) -> List[ProductVariant]:
        """
        Creates variants from scraped attributes.
        """

        price = self._parse_price(data.get("price", "0"))

        attributes = data.get("attributes", {})

        # fallback: single variant
        if not attributes:
            return [
                ProductVariant(
                    sku=self._generate_sku(data["title"]),
                    price=price,
                    stock=0,
                    option_codes=[]
                )
            ]

        # MVP strategy: first attribute only
        first_attr_key = list(attributes.keys())[0]
        values = attributes[first_attr_key]

        variants = []

        for v in values:
            variants.append(
                ProductVariant(
                    sku=self._generate_sku(data["title"], v),
                    price=price,
                    stock=0,
                    option_codes=[self._normalize_option_code(v)]
                )
            )

        return variants

    # -------------------------
    # UTILITIES
    # -------------------------

    def _normalize_option_code(self, value: str) -> str:
        return value.lower().replace(" ", "").replace("°", "").replace("k", "k")

    def _pretty_name(self, code: str) -> str:
        return code.replace("_", " ").replace("-", " ").title()

    def _generate_sku(self, name: str, suffix: str = "") -> str:
        base = slugify(name).upper()
        if suffix:
            return f"{base}-{self._normalize_option_code(suffix)}"
        return base

    def _parse_price(self, price_str: str) -> float:
        if not price_str:
            return 0.0
        return float(re.sub(r"[^0-9.]", "", price_str))