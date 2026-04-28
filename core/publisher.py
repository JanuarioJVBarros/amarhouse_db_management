import logging
import time
import argparse
from types import SimpleNamespace

import requests

from beevo.assets import AssetsAPI
from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from beevo.labels import LabelsAPI
from beevo.options import OptionsAPI
from beevo.product import ProductAPI
from beevo.variants import VariantsAPI
from beevo.exceptions import BeevoResponseError, BeevoTransportError, BeevoValidationError
from utils import json_utils

logger = logging.getLogger(__name__)


class ProductPublisher:
    """
    Orchestrates the product ingestion flow from scraped product data to Beevo.
    """

    def __init__(self, client):
        self.client = client
        self.product_api = ProductAPI(client)
        self.options_api = OptionsAPI(client)
        self.variants_api = VariantsAPI(client)
        self.assets_api = AssetsAPI(client)
        self.labels_api = LabelsAPI(client)

    def publish(self, product):
        logger.info("[PUBLISH] Starting: %s", product.slug)

        product_id, created, skip_reason = self._get_or_create_product(product)
        if not created:
            if skip_reason == "slug_exists":
                logger.info("RESULT: [SKIP] Product already exists: %s", product.slug)
            elif skip_reason and skip_reason.startswith("sku_exists:"):
                logger.info(
                    "RESULT: [SKIP] Product %s has an existing SKU in Beevo: %s",
                    product.slug,
                    skip_reason.split(":", 1)[1],
                )
            else:
                logger.info("RESULT: [SKIP] Product not published: %s", product.slug)
            return None

        option_groups = self._create_option_groups(product, product_id)
        self._create_variants(product, product_id, option_groups)
        self._attach_labels(product, product_id)
        self._upload_and_attach_assets(product, product_id)

        logger.info("[PUBLISH] Completed: %s", product.slug)
        return {"product_id": product_id, "status": "published"}

    def _product_skus(self, product):
        # SKU collisions are a stronger uniqueness signal than slugs because
        # the same product family can be discovered again under a new title or
        # normalized slug while still referring to the same sellable variants.
        skus = []

        primary_sku = getattr(product, "sku", None)
        if primary_sku:
            skus.append(primary_sku)

        for variant in getattr(product, "variants", []):
            sku = variant.get("sku")
            if sku:
                skus.append(sku)

        normalized = []
        seen = set()
        for sku in skus:
            cleaned = str(sku).strip().upper()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            normalized.append(cleaned)

        return normalized

    def _get_or_create_product(self, product):
        logger.info("[STEP] Product create/check: %s", product.slug)
        existing = self.product_api.get_by_slug(product.slug)

        if existing:
            return existing["id"], False, "slug_exists"

        for sku in self._product_skus(product):
            existing_variant = self.variants_api.get_variant_by_sku(sku)
            if existing_variant:
                return None, False, f"sku_exists:{sku}"

        product_data = {
            "name": product.name,
            "slug": product.slug,
            "description": product.description,
            "description_full": getattr(product, "description_full", None),
        }
        created = self.product_api.create_product(product_data)

        logger.info("RESULT: [DONE] Create product: %s", product.slug)
        return created["id"], True, None

    def _normalize_option_token(self, value):
        if value is None:
            return None
        token = str(value).strip().casefold()
        return token or None

    def _filtered_group_options(self, options):
        filtered = []
        for option in options or []:
            if isinstance(option, dict):
                option_name = option.get("name")
                # Some scrapers emit "-" when the supplier table shows an empty
                # placeholder. Beevo option groups cannot be created from that.
                if self._normalize_option_token(option_name) in {None, "-"}:
                    continue
                filtered.append(option)
                continue

            if self._normalize_option_token(option) in {None, "-"}:
                continue
            filtered.append(option)
        return filtered

    def _create_option_groups(self, product, product_id):
        logger.info("[STEP] Creating option groups")

        created_groups = []

        for group in getattr(product, "option_groups", []):
            group_name = group.get("name")
            options = self._filtered_group_options(group.get("options") or [])
            if not options:
                # Skipping an invalid group is safer than aborting the whole
                # product. That lets us preserve the valid dimensions that
                # still describe distinct Beevo variants correctly.
                logger.info("RESULT: [SKIP] No valid options for group %s", group_name)
                continue

            result = self.options_api.create_option_group(
                name=group_name,
                options=options,
            )

            self.options_api.add_option_group_to_product(product_id, result["id"])
            created_groups.append(result)

        return created_groups

    def _build_option_lookup(self, option_groups):
        lookup = {}

        for group in option_groups or []:
            group_name = self._normalize_option_token(group.get("name"))
            if not group_name:
                continue

            option_lookup = {}
            for option in group.get("options") or []:
                option_name = self._normalize_option_token(option.get("name"))
                option_id = option.get("id")
                if option_name and option_id:
                    option_lookup[option_name] = option_id

            if option_lookup:
                lookup[group_name] = option_lookup

        return lookup

    def _is_flat_option_list(self, option_groups):
        if not option_groups:
            return False
        first_entry = option_groups[0]
        # Older tests and helper flows passed a flattened list of options
        # instead of Beevo group payloads. We keep supporting that shape so
        # the stricter group-aware matching does not break existing tooling.
        return isinstance(first_entry, dict) and "options" not in first_entry and "id" in first_entry

    def _variant_option_ids_from_flat_options(self, variant_options, flat_options):
        matched_ids = []
        values = {
            self._normalize_option_token(value)
            for value in (variant_options or {}).values()
            if self._normalize_option_token(value)
        }
        for option in flat_options or []:
            option_name = self._normalize_option_token(option.get("name"))
            option_id = option.get("id")
            if option_name in values and option_id:
                matched_ids.append(option_id)
        return matched_ids

    def _variant_option_ids(self, variant_options, option_groups):
        option_lookup = self._build_option_lookup(option_groups)
        matched_ids = []

        # Beevo expects exactly one option from each attached group, so we
        # resolve values by group name rather than by value alone.
        for group in option_groups or []:
            group_name = group.get("name")
            group_key = self._normalize_option_token(group_name)
            selected_value = (variant_options or {}).get(group_name)
            selected_key = self._normalize_option_token(selected_value)
            option_id = option_lookup.get(group_key, {}).get(selected_key)

            if option_id:
                matched_ids.append(option_id)
                logger.info("Matched variant option: %s -> %s", group_name, option_id)

        return matched_ids

    def _create_variants(self, product, product_id, option_groups=None, **kwargs):
        logger.info("[STEP] Creating variants")
        if option_groups is None:
            option_groups = kwargs.get("option_ids") or []

        uses_flat_option_list = self._is_flat_option_list(option_groups)
        expected_option_count = len(option_groups or []) if not uses_flat_option_list else len(
            getattr(product, "option_groups", []) or []
        )
        seen_option_signatures = set()

        for variant in getattr(product, "variants", []):
            if uses_flat_option_list:
                variant_option_ids = self._variant_option_ids_from_flat_options(variant.get("options"), option_groups)
                if not expected_option_count:
                    expected_option_count = len(variant.get("options") or {})
            else:
                variant_option_ids = self._variant_option_ids(variant.get("options"), option_groups)

            if option_groups and variant.get("options") and not variant_option_ids:
                logger.info(
                    "RESULT: [SKIP] No matching option found for variant %s",
                    variant.get("name"),
                )
                continue

            if option_groups and expected_option_count and len(variant_option_ids) != expected_option_count:
                logger.info(
                    "RESULT: [SKIP] Variant %s is missing option values for one or more groups",
                    variant.get("name"),
                )
                continue

            option_signature = tuple(sorted(variant_option_ids))
            should_dedupe_by_options = bool(expected_option_count)
            if should_dedupe_by_options and option_signature in seen_option_signatures:
                # Beevo treats the combination of option selections as the
                # variant identity inside a product. Duplicating that signature
                # would create a hard API error, so we filter it here first.
                logger.info(
                    "RESULT: [SKIP] Duplicate option combination for variant %s",
                    variant.get("name"),
                )
                continue
            if should_dedupe_by_options:
                seen_option_signatures.add(option_signature)

            self.variants_api.create_variant(
                product_id=product_id,
                name=variant.get("name"),
                sku=variant.get("sku"),
                price=variant.get("price", 0),
                stock=1000,
                option_ids=variant_option_ids,
            )

    def _upload_and_attach_assets(self, product, product_id):
        logger.info("[STEP] Uploading assets")

        asset_ids = []
        for img_url in getattr(product, "images", []):
            try:
                asset_ids.append(self.assets_api.upload_asset(img_url))
            except (requests.RequestException, BeevoResponseError, BeevoTransportError, BeevoValidationError) as exc:
                logger.warning("RESULT: [SKIP] Failed to upload asset %s: %s", img_url, exc)

        if not asset_ids:
            logger.info("RESULT: [SKIP] No assets found")
            return

        self.assets_api.update_product_assets(product_id, asset_ids=asset_ids)
        self.assets_api.set_asset_as_featured(product_id, asset_ids[0])
        logger.info("RESULT: [DONE] Assets uploaded")

    def _attach_labels(self, product, product_id):
        logger.info("[STEP] Attaching labels")
        facet_value_ids = getattr(product, "facet_value_ids", None) or []
        if not facet_value_ids:
            logger.info("RESULT: [SKIP] No labels found")
            return

        normalized_ids = [str(label_id) for label_id in facet_value_ids if label_id is not None]
        if not normalized_ids:
            logger.info("RESULT: [SKIP] No labels found")
            return

        self.labels_api.add_labels_to_product(product_id, normalized_ids)
        logger.info("RESULT: [DONE] Labels attached")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    cli = argparse.ArgumentParser(description="Publish scraped products to Beevo from a JSON file.")
    cli.add_argument(
        "--input-file",
        default="aronlight_preview.json",
        help="JSON file containing scraped products.",
    )
    cli.add_argument(
        "--sleep-seconds",
        type=float,
        default=1.0,
        help="Delay between publish attempts.",
    )
    args = cli.parse_args()

    settings = load_environment()
    client = BeevoClient(
        base_url=settings.beevo_url,
        beevo_cookie=settings.beevo_cookie,
        timeout=settings.request_timeout,
    )
    publisher = ProductPublisher(client)

    scraped_products = json_utils.load_json(args.input_file)

    print("\n=== PUBLISH RESULT ===")

    for product in scraped_products:
        product = SimpleNamespace(**product)
        publisher.publish(product)
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)
