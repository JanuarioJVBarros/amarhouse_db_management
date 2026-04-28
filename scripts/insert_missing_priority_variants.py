import argparse
import logging

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from core.publisher import ProductPublisher
from scrapers.aronlight.publish_priority_products import build_all_priority_products

logger = logging.getLogger(__name__)

DEFAULT_TARGET_SKUS = [
    "ILAR-02837",
    "ILAR-02979",
    "ILAR-03671",
    "ILAR-03670",
]


def normalize_sku(value):
    return str(value or "").strip().upper()


def normalize_option_token(value):
    return str(value or "").strip().casefold()


def build_target_products(target_skus=None):
    wanted = {normalize_sku(sku) for sku in (target_skus or DEFAULT_TARGET_SKUS)}
    selected = []

    for product in build_all_priority_products():
        product_variant_skus = {
            normalize_sku(variant.get("sku"))
            for variant in getattr(product, "variants", []) or []
            if normalize_sku(variant.get("sku"))
        }
        if product_variant_skus & wanted:
            selected.append(product)

    return selected


def option_lookup(existing_product):
    lookup = {}

    for group in existing_product.get("optionGroups") or []:
        group_name = normalize_option_token(group.get("name"))
        if not group_name:
            continue

        group_options = {}
        for option in group.get("options") or []:
            option_name = normalize_option_token(option.get("name"))
            option_id = option.get("id")
            if option_name and option_id:
                group_options[option_name] = option_id

        if group_options:
            lookup[group_name] = group_options

    return lookup


def variant_option_ids(existing_product, variant):
    lookup = option_lookup(existing_product)
    if not lookup:
        return []

    matched = []
    variant_options = variant.get("options") or {}
    for group in existing_product.get("optionGroups") or []:
        # When a product already exists in Beevo, we must reuse the real option
        # IDs attached there. Recreating variants with guessed IDs would either
        # fail or create the wrong variant signature.
        group_name = group.get("name")
        group_key = normalize_option_token(group_name)
        option_value = normalize_option_token(variant_options.get(group_name))
        option_id = lookup.get(group_key, {}).get(option_value)
        if option_id:
            matched.append(option_id)

    return matched


def ensure_product_and_variants(publisher, product, dry_run=False):
    existing_product = publisher.product_api.get_by_slug(product.slug)

    if not existing_product:
        # If the seeded product does not exist yet, the normal publisher path is
        # still the safest way to create its product shell, labels, and variants
        # together.
        logger.info("[priority-insert] Product %s does not exist yet; publishing full product", product.slug)
        if dry_run:
            return {"product_id": product.slug, "status": "dry-run-create"}
        return publisher.publish(product)

    product_id = existing_product["id"]
    publisher._attach_labels(product, product_id)
    inserted = []

    for variant in getattr(product, "variants", []) or []:
        sku = normalize_sku(variant.get("sku"))
        if not sku:
            continue

        if publisher.variants_api.get_variant_by_sku(sku):
            logger.info("[priority-insert] [SKIP] SKU already exists: %s", sku)
            continue

        option_ids = variant_option_ids(existing_product, variant)
        expected_option_count = len(existing_product.get("optionGroups") or [])
        if expected_option_count and len(option_ids) != expected_option_count:
            # Skipping is safer than sending a partial combination to Beevo,
            # because Beevo rejects variants that do not cover every group.
            logger.warning(
                "[priority-insert] [SKIP] Variant %s is missing Beevo option IDs for %s",
                sku,
                product.slug,
            )
            continue

        logger.info("[priority-insert] Adding missing variant %s to %s", sku, product.slug)
        if dry_run:
            inserted.append({"sku": sku, "status": "dry-run", "option_ids": option_ids})
            continue

        publisher.variants_api.create_variant(
            product_id=product_id,
            name=variant.get("name"),
            sku=sku,
            price=variant.get("price", 0),
            stock=1000,
            option_ids=option_ids,
        )
        inserted.append({"sku": sku, "status": "inserted"})

    return {
        "product_id": product_id,
        "status": "updated",
        "inserted_variants": inserted,
    }


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Insert missing priority Aronlight variants into existing Beevo products.",
    )
    cli.add_argument(
        "--sku",
        action="append",
        dest="skus",
        help="Override target SKU(s). Can be passed multiple times.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would be inserted without sending mutations to Beevo.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    settings = load_environment()
    publisher = ProductPublisher(
        BeevoClient(
            base_url=settings.beevo_url,
            beevo_cookie=settings.beevo_cookie,
            timeout=settings.request_timeout,
        )
    )

    products = build_target_products(args.skus)
    results = [ensure_product_and_variants(publisher, product, dry_run=args.dry_run) for product in products]

    print(f"Target products processed: {len(products)}")
    return results


if __name__ == "__main__":
    main()
