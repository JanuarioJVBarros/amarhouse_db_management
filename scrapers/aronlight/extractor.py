from scrapers.base import BaseProductExtractor, build_scraped_product, clean_text

from .parser import AronlightParser


class AronlightExtractor(BaseProductExtractor):
    # Fields earlier in this ranking are more likely to represent the actual
    # dimensions a Beevo customer selects. Descriptive fields stay excluded
    # unless they genuinely split the SKU space.
    OPTION_FIELD_PRIORITY = {
        "POWER": 0,
        "CCT": 1,
        "3CCT": 1,
        "COLOR TEMPERATURE": 1,
        "COLOR": 2,
        "COLOUR": 2,
        "HOUSING COLOUR": 2,
        "SIZE": 3,
        "CUTOUT": 4,
        "BASE": 5,
        "TYPE BULB": 6,
    }
    EXCLUDED_OPTION_FIELDS = {
        "SKU",
        "LUMENS",
        "LUMEN",
        "TOTAL LUMINOUS FLUX",
        "CRI",
        "IP",
        "VOLTAGE",
        "MATERIAL",
        "BODY MATERIAL",
        "PF",
        "LIFETIME",
        "CERTIFICATIONS",
        "ENERGY LABEL",
        "QUANTITY BOX",
        "BEAM ANGLE",
        "CLASS",
        "CLASSE",
        "IK",
        "RATED LOAD",
        "DETECTION DISTANCE",
        "DELAY TIME",
        "AMBIENT LIGHTING",
        "INSTALLATION HEIGHT",
        "DETECTION ANGLE",
        "DETECTION RANGE",
    }
    SKIP_SECTION_KEYWORDS = {"ACCESSORIES", "ACESSORIES"}
    OPTION_NAME_MAP = {
        "3CCT": "CCT",
        "HOUSING COLOUR": "Color",
        "COLOUR": "Color",
    }

    def _is_watts_heading(self, heading):
        text = clean_text(heading or "")
        return bool(text and "WATT" in text.upper())

    def _normalize_field_name(self, field_name):
        field = clean_text(field_name or "")
        if not field:
            return None
        return self.OPTION_NAME_MAP.get(field.upper(), field.title())

    def _columnar_variants_from_rows(self, section_name, rows):
        width = max(len(row) for row in rows)
        variant_count = max(width - 1, 0)
        if variant_count == 0:
            return []

        # Aronlight often encodes a whole variant matrix as:
        # FIELD | VARIANT 1 | VARIANT 2 | ...
        # so we transpose that table back into per-variant dictionaries here.
        variants = [dict() for _ in range(variant_count)]
        for row in rows:
            field = clean_text(row[0])
            if not field:
                continue

            values = row[1:] + [None] * max(0, variant_count - (len(row) - 1))
            for index in range(variant_count):
                value = clean_text(values[index]) if index < len(values) else None
                if value:
                    variants[index][field] = value

        for variant in variants:
            if self._is_watts_heading(section_name) and "POWER" not in variant:
                # Some tabbed sections communicate wattage only in the heading,
                # not in a dedicated row.
                variant["POWER"] = section_name

        return variants

    def _single_variant_from_rows(self, section_name, rows):
        variant = {}
        for row in rows:
            if len(row) < 2:
                continue
            field = clean_text(row[0])
            value = clean_text(" ".join(row[1:]))
            if field and value:
                variant[field] = value

        if self._is_watts_heading(section_name) and "POWER" not in variant:
            variant["POWER"] = section_name

        return variant if variant.get("SKU") else None

    def _variant_entries(self, parser):
        variants = []
        for table in parser.product_tables():
            section_name = clean_text(table.get("section"))
            if section_name and any(keyword in section_name.upper() for keyword in self.SKIP_SECTION_KEYWORDS):
                continue

            rows = table.get("rows") or []
            if not rows:
                continue

            has_sku_row = any(clean_text(row[0]).upper() == "SKU" for row in rows if row)
            if not has_sku_row:
                # If a table has no SKU row, we treat it as descriptive content
                # rather than a Beevo variant source of truth.
                continue

            if any(len(row) > 2 for row in rows):
                variants.extend(self._columnar_variants_from_rows(section_name, rows))
                continue

            single_variant = self._single_variant_from_rows(section_name, rows)
            if single_variant:
                variants.append(single_variant)

        return variants

    def _option_fields(self, variant_entries):
        candidate_fields = []
        keys = set().union(*(entry.keys() for entry in variant_entries))
        for field in sorted(
            keys,
            key=lambda value: (
                self.OPTION_FIELD_PRIORITY.get(value.upper(), 100),
                value,
            ),
        ):
            if field.upper() in self.EXCLUDED_OPTION_FIELDS or field.upper() == "SKU":
                continue
            values = {clean_text(entry.get(field)) for entry in variant_entries if clean_text(entry.get(field))}
            if len(values) > 1:
                candidate_fields.append(field)

        selected_fields = []
        for field in candidate_fields:
            if not selected_fields:
                selected_fields.append(field)
                continue

            is_redundant = True
            seen_signatures = {}
            for entry in variant_entries:
                # If a new field never changes independently of the already
                # selected dimensions, it adds UI noise without creating new
                # Beevo combinations.
                signature = tuple(clean_text(entry.get(selected)) for selected in selected_fields)
                value = clean_text(entry.get(field))
                if signature not in seen_signatures:
                    seen_signatures[signature] = value
                    continue
                if seen_signatures[signature] != value:
                    is_redundant = False
                    break

            if not is_redundant:
                selected_fields.append(field)

        return selected_fields

    def _option_groups(self, variant_entries, option_fields):
        groups = []
        for field in option_fields:
            options = []
            seen = set()
            for entry in variant_entries:
                value = clean_text(entry.get(field))
                if not value or value in seen:
                    continue
                seen.add(value)
                options.append(value)
            groups.append({"name": self._normalize_field_name(field), "options": options})
        return groups

    def _variant_name(self, title, entry, option_fields):
        suffix = []
        for field in option_fields:
            value = clean_text(entry.get(field))
            if not value:
                continue
            if value.lower() in title.lower():
                continue
            suffix.append(value)

        if not suffix:
            power_value = clean_text(entry.get("POWER"))
            if power_value and power_value.lower() not in title.lower():
                # Single-SKU sections like "6 WATTS" still need a useful
                # variant name even when no Beevo option group is created.
                suffix.append(power_value)

        return f"{title} {' '.join(suffix)}".strip()

    def extract(self, html, url):
        parser = AronlightParser(html)
        title = parser.page_title()
        if not title:
            return None

        variant_entries = [entry for entry in self._variant_entries(parser) if clean_text(entry.get("SKU"))]
        option_fields = self._option_fields(variant_entries) if variant_entries else []
        option_groups = self._option_groups(variant_entries, option_fields) if variant_entries else []

        variants = []
        for entry in variant_entries:
            sku = clean_text(entry.get("SKU"))
            if not sku:
                continue
            options = {}
            for field in option_fields:
                value = clean_text(entry.get(field))
                if value:
                    options[self._normalize_field_name(field)] = value

            variants.append(
                {
                    "name": self._variant_name(title, entry, option_fields),
                    "sku": sku,
                    "price": 0,
                    "options": options,
                }
            )

        if not variants:
            variants = [
                {
                    "name": title,
                    "sku": None,
                    "price": 0,
                    "options": {},
                }
            ]

        return build_scraped_product(
            name=title,
            description=parser.description(),
            description_full=parser.description_full(),
            sku=variants[0]["sku"],
            images=parser.images(url),
            labels=parser.breadcrumb_labels() or ["Aronlight"],
            option_groups=option_groups,
            facet_value_ids=["164"],
            variants=variants,
            source_url=url,
            supplier="aronlight",
        )
