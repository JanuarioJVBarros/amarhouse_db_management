import argparse
import json
import logging
from pathlib import Path

from beevo.client import BeevoClient
from beevo.config.env_loader import load_environment
from core.publisher import ProductPublisher
from scrapers.base import build_scraped_product, slugify

logger = logging.getLogger(__name__)


PRIORITY_PRODUCTS = [
    {
        "name": "MODULE EYE ZOOM",
        "source_url": "https://aronlight.com/en/project-details/eye/",
        "skus": ["ILAR-02964", "ILAR-02837"],
    },
    {
        "name": "GLAZ",
        "source_url": None,
        "skus": ["ILAR-02239", "ILAR-02240"],
    },
    {
        "name": "BACKLIT 600X600",
        "source_url": "https://aronlight.com/project-details/led-panel-backlit/",
        "skus": ["ILAR-02914", "ILAR-03597", "ILAR-03611"],
    },
    {
        "name": "BACKLIT 1200X300",
        "source_url": "https://aronlight.com/project-details/painel-edgelit-35w-120x30-ip65/",
        "skus": ["ILAR-02979", "ILAR-02161"],
    },
    {
        "name": "BOARD SURFACE",
        "source_url": "https://aronlight.com/project-details/board/",
        "skus": ["ILAR-03671", "ILAR-03670", "ILAR-02945"],
    },
    {
        "name": "LUNA",
        "source_url": None,
        "skus": ["ILAR-03679", "ILAR-03680"],
    },
    {
        "name": "PASCAL GU10",
        "source_url": "https://aronlight.com/project-details/luminaria-pendente-pascal/",
        "skus": ["ILAR-03740", "ILAR-03741", "ILAR-03742", "ILAR-03743", "ILAR-03744", "ILAR-03745"],
    },
    {
        "name": "LUNO",
        "source_url": None,
        "skus": ["ILAR-03754", "ILAR-03753"],
    },
    {
        "name": "VIRA",
        "source_url": None,
        "skus": ["ILAR-03755", "ILAR-03756"],
    },
    {
        "name": "JULLE",
        "source_url": None,
        "skus": ["ILAR-03758", "ILAR-03757"],
    },
    {
        "name": "NOVVA",
        "source_url": None,
        "skus": ["ILAR-03759"],
    },
    {
        "name": "VIGG GU10",
        "source_url": "https://aronlight.com/project-details/vigg/",
        "skus": ["ILAR-02452", "ILAR-02453"],
    },
    {
        "name": "LEV GU10",
        "source_url": "https://aronlight.com/project-details/downlight-saliente-lev/",
        "skus": ["ILAR-02454", "ILAR-02455"],
    },
    {
        "name": "MINI LEV GU10",
        "source_url": "https://aronlight.com/project-details/downlight-saliente-lev/",
        "skus": ["ILAR-03674", "ILAR-03675"],
    },
    {
        "name": "PRADO GU10",
        "source_url": "https://aronlight.com/project-details/prado-smart/",
        "skus": ["ILAR-03068", "ILAR-03069"],
    },
]


def normalize_sku(value):
    return str(value or "").strip().upper()


def build_priority_product(entry):
    skus = [normalize_sku(sku) for sku in entry["skus"] if normalize_sku(sku)]
    variants = []
    option_groups = []

    if len(skus) > 1:
        option_groups = [
            {
                "name": "Referencia",
                "options": skus,
            }
        ]

    for sku in skus:
        variant = {
            "name": f"{entry['name']} {sku}",
            "sku": sku,
            "price": 0,
            "options": {"Referencia": sku} if option_groups else {},
        }
        variants.append(variant)

    description = (
        f"{entry['name']} imported from curated Aronlight SKU list. "
        f"Source reference: {entry['source_url'] or 'catalog/manual reference'}."
    )

    return build_scraped_product(
        name=entry["name"],
        slug=slugify(entry["name"]),
        description=description,
        description_full=None,
        sku=skus[0] if skus else None,
        images=[],
        labels=["Aronlight"],
        option_groups=option_groups,
        facet_value_ids=["164"],
        variants=variants,
        source_url=entry.get("source_url"),
        supplier="aronlight",
    )


def build_all_priority_products():
    return [build_priority_product(entry) for entry in PRIORITY_PRODUCTS]


def save_products(path, products):
    serializable = [product.__dict__ if hasattr(product, "__dict__") else product for product in products]
    Path(path).write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")


def publish_products(products, dry_run=False):
    if dry_run:
        return [{"product_id": product.slug, "status": "dry-run"} for product in products]

    settings = load_environment()
    publisher = ProductPublisher(
        BeevoClient(
            base_url=settings.beevo_url,
            beevo_cookie=settings.beevo_cookie,
            timeout=settings.request_timeout,
        )
    )

    results = []
    for product in products:
        logger.info("[aronlight-priority] Publishing %s", product.slug)
        result = publisher.publish(product)
        if result:
            results.append(result)
    return results


def main(argv=None):
    cli = argparse.ArgumentParser(
        description="Publish a curated manual set of priority Aronlight products using known SKU families.",
    )
    cli.add_argument(
        "--output-file",
        default="aronlight_priority_products.json",
        help="JSON file to write the generated curated products.",
    )
    cli.add_argument(
        "--publish",
        action="store_true",
        help="Publish the generated products to Beevo.",
    )
    cli.add_argument(
        "--dry-run",
        action="store_true",
        help="When combined with --publish, report publish candidates without sending them to Beevo.",
    )
    args = cli.parse_args(argv)

    logging.basicConfig(level=logging.INFO)

    products = build_all_priority_products()
    save_products(args.output_file, products)
    print(f"Generated {len(products)} priority Aronlight products")

    if args.publish:
        results = publish_products(products, dry_run=args.dry_run)
        print(f"Publish results: {len(results)}")

    return {"generated_products": len(products)}


if __name__ == "__main__":
    main()
