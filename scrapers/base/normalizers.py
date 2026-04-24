import re

from scrapers.models import ScrapedProduct


def clean_text(value):
    if value is None:
        return None

    text = " ".join(str(value).split()).strip()
    return text or None


def unique_strings(values):
    seen = set()
    cleaned = []

    for value in values or []:
        normalized = clean_text(value)
        if not normalized:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(normalized)

    return cleaned


def normalize_images(values):
    return unique_strings(values)


def normalize_labels(values):
    return unique_strings(values)


def slugify(value):
    text = clean_text(value)
    if not text:
        return None

    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def build_scraped_product(
    *,
    name,
    slug=None,
    description=None,
    description_full=None,
    price=None,
    reference=None,
    sku=None,
    images=None,
    labels=None,
    colors=None,
    variants=None,
    option_groups=None,
    facet_value_ids=None,
    source_url=None,
    supplier=None,
):
    normalized_name = clean_text(name)

    return ScrapedProduct(
        name=normalized_name,
        slug=slug or slugify(normalized_name),
        description=clean_text(description),
        description_full=clean_text(description_full),
        price=clean_text(price),
        reference=clean_text(reference),
        sku=clean_text(sku),
        images=normalize_images(images),
        labels=normalize_labels(labels),
        option_groups=option_groups or [],
        facet_value_ids=facet_value_ids or [],
        colors=colors,
        variants=variants or [],
        source_url=clean_text(source_url),
        supplier=clean_text(supplier),
    )
