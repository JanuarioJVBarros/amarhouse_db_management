from typing import Dict, Any, List
from core.transformers.transformer import ProductTransformer


class GolmarTransformer(ProductTransformer):
    """
    Site-specific transformer for Golmar scraped data → Beevo payload
    """

    def __init__(self, language_code: str = "pt_PT"):
        super().__init__(language_code=language_code)

    # -------------------------
    # MAIN ENTRY
    # -------------------------
    def transform(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Override base transform with Golmar-specific logic
        """

        base_payload = super().transform(raw)

        # -------------------------
        # Enhance Golmar-specific fields
        # -------------------------

        base_payload["translations"][0]["name"] = self._normalize_name(raw)
        base_payload["translations"][0]["slug"] = self._normalize_slug(raw)

        base_payload["translations"][0]["description"] = self._extract_short_description(raw)

        base_payload["translations"][0]["customFields"]["description_2"] = self._extract_full_description(raw)
        base_payload["translations"][0]["customFields"]["other_information"] = self._extract_other_information(raw)

        # -------------------------
        # Improve facet mapping (Golmar-specific cleaning)
        # -------------------------
        base_payload["facetValueIds"] = self._map_golmar_facets(raw)

        # -------------------------
        # Image override (Golmar has single primary image usually)
        # -------------------------
        image_data = self._extract_primary_image(raw)
        base_payload["assetIds"] = image_data["asset_ids"]
        base_payload["featuredAssetId"] = image_data["featured_asset_id"]

        return base_payload

    # -------------------------
    # NAME / SLUG
    # -------------------------

    def _normalize_name(self, raw: Dict[str, Any]) -> str:
        name = raw.get("name", "")
        return name.strip()

    def _normalize_slug(self, raw: Dict[str, Any]) -> str:
        slug = raw.get("slug") or raw.get("name", "")
        return self._slugify(slug)

    # -------------------------
    # DESCRIPTION LOGIC
    # -------------------------

    def _extract_short_description(self, raw: Dict[str, Any]) -> str:
        """
        Golmar: short description = HTML list in product body
        """
        return raw.get("description_html", "") or ""

    def _extract_full_description(self, raw: Dict[str, Any]) -> str:
        """
        Enriched full description with structured formatting
        """
        desc = raw.get("description_html", "")

        if not desc:
            return ""

        return f"""
        <div class="golmar-description">
            {desc}
        </div>
        """.strip()

    def _extract_other_information(self, raw: Dict[str, Any]) -> str:
        parts = []

        if raw.get("reference"):
            parts.append(f"<b>Reference:</b> {raw['reference']}")

        if raw.get("product_code"):
            parts.append(f"<b>Product Code:</b> {raw['product_code']}")

        if raw.get("categories"):
            parts.append(
                "<b>Categories:</b> " + " > ".join(raw["categories"])
            )

        if raw.get("downloads"):
            parts.append(f"<b>Downloads:</b> {len(raw['downloads'])} files")

        return "<br>".join(parts)

    # -------------------------
    # IMAGE HANDLING (Golmar-specific simplification)
    # -------------------------

    def _extract_primary_image(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Golmar products usually have a single main image
        """

        image_url = raw.get("image")

        if not image_url:
            return {
                "asset_ids": [],
                "featured_asset_id": None,
            }

        asset_id = self._fake_asset_id(image_url)

        return {
            "asset_ids": [asset_id],
            "featured_asset_id": asset_id,
        }

    # -------------------------
    # FACET MAPPING (Golmar-specific cleanup)
    # -------------------------

    def _map_golmar_facets(self, raw: Dict[str, Any]) -> List[str]:
        """
        Cleans category noise from Golmar breadcrumbs
        """

        categories = raw.get("categories", [])

        cleaned = []

        for c in categories:
            if not c:
                continue

            c = c.strip()

            # filter noise categories seen in Golmar HTML
            if c.lower() in ["home", "products", "golmar"]:
                continue

            cleaned.append(self._fake_facet_id(c))

        return cleaned