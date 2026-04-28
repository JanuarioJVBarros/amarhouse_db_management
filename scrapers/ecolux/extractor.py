import re

from scrapers.base import BaseProductExtractor, build_scraped_product, clean_text, slugify

from .parser import EcoluxParser


class EcoluxExtractor(BaseProductExtractor):
    OPTION_NAME_MAP = {
        "W": "Potência (W)",
        "Temp (K)": "Temperatura (K)",
        "Acabado": "Acabamento",
        "Modelo": "Modelo",
        "Tamaño": "Tamanho",
        "Tamano": "Tamanho",
        "Medida": "Medida",
        "Color": "Cor",
    }

    TEXT_REPLACEMENTS = [
        ("Blanco/White", "Branco"),
        ("Negro/Black", "Preto"),
        ("White", "Branco"),
        ("Black", "Preto"),
        ("Blanco", "Branco"),
        ("Negro", "Preto"),
        ("Bombillería", "Lâmpadas"),
        ("BombillerÃ­a", "Lâmpadas"),
        ("Led Bulbs", "Lâmpadas LED"),
        ("Estándar", "Padrão"),
        ("EstÃ¡ndar", "Padrão"),
        ("Superficie", "Superfície"),
        ("SUPERFICIE", "SUPERFÍCIE"),
        ("Empotrables", "Embutidos"),
        ("EMPOTRABLES", "EMBUTIDOS"),
        ("Cuadrado", "Quadrado"),
        ("CUADRADO", "QUADRADO"),
        ("sujección", "fixação"),
        ("sujecciÃ³n", "fixação"),
        ("alimentación", "alimentação"),
        ("alimentaciÃ³n", "alimentação"),
        ("aluminio", "alumínio"),
        ("aluminio", "alumínio"),
        ("Bombilla", "Lâmpada"),
        ("bombilla", "lâmpada"),
        ("Descripción", "Descrição"),
        ("DescripciÃ³n", "Descrição"),
        ("Acabado", "Acabamento"),
    ]

    EXCLUDED_OPTION_COLUMNS = {
        "Ref",
        "Descripción",
        "DescripciÃ³n",
        "Descricao",
        "Descrição",
        "DescriÃ§Ã£o",
        "Voltaje",
        "Lm",
        "Dim",
        "CRI",
        "IP",
        "PF",
        "Hz",
        "Vida",
        "LM/W",
    }

    def _translate_text(self, value):
        text = clean_text(value or "")
        if not text:
            return None

        translated = text
        for source, target in self.TEXT_REPLACEMENTS:
            translated = translated.replace(source, target)

        return clean_text(translated)

    def _display_option_name(self, name):
        normalized = clean_text(name)
        if not normalized:
            return None
        return self.OPTION_NAME_MAP.get(normalized, self._translate_text(normalized))

    def _display_option_value(self, value):
        return self._translate_text(value)

    def _display_labels(self, labels):
        return [label for label in (self._translate_text(value) for value in labels or []) if label]

    def _variant_display_suffix(self, title, option_values):
        suffix_values = []
        title_normalized = clean_text(title or "").lower()

        for key, value in option_values.items():
            if key == "Modelo" and value and title_normalized and value.lower().startswith(title_normalized):
                trimmed = clean_text(value[len(title):])
                value = trimmed or value

            display_value = self._display_option_value(value)
            if not display_value:
                continue
            if display_value.lower() in title_normalized:
                continue
            if display_value in suffix_values:
                continue
            suffix_values.append(display_value)

        return " ".join(suffix_values)

    def _option_sort_key(self, value):
        text = clean_text(value or "")
        normalized = (
            text.replace(".", "")
            .replace(",", ".")
            .replace("K", "")
            .replace("V", "")
            .replace("W", "")
            .replace("Âº", "")
            .strip()
        )

        try:
            return (0, float(normalized), text)
        except ValueError:
            return (1, text.lower())

    def _extract_description(self, parser):
        for paragraph in parser.select("p"):
            text = clean_text(paragraph.get_text(" ", strip=True))
            if not text:
                continue
            if text.upper() in {"BLANCO", "NEGRO"}:
                continue
            return self._translate_text(text)
        return None

    def _description_value(self, values):
        return clean_text(
            values.get("Descripción")
            or values.get("DescripciÃ³n")
            or values.get("Descrição")
            or values.get("Descricao")
            or values.get("DescriÃ§Ã£o")
        )

    def _normalize_description_key(self, value):
        text = clean_text(value or "")
        if not text:
            return None

        normalized = text.lower()
        normalized = re.sub(r"\bde\s+(\d+\s+metro[s]?)\b", r"\1", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    def _is_catalog_page(self, records):
        descriptions = [
            self._normalize_description_key(self._description_value(record["values"]))
            for record in records
            if self._normalize_description_key(self._description_value(record["values"]))
        ]

        if len(records) < 2 or not descriptions:
            return False

        return len(set(descriptions)) > 1

    def _build_single_variant_product(self, name, description, ref, labels, images, url, slug=None):
        display_name = self._translate_text(name)
        return build_scraped_product(
            name=display_name,
            slug=slug,
            description=self._translate_text(description),
            description_full=None,
            sku=ref,
            images=images,
            labels=self._display_labels(labels),
            variants=[
                {
                    "name": display_name,
                    "sku": ref,
                    "price": 0,
                    "options": {},
                }
            ],
            source_url=url,
            supplier="ecolux",
        )

    def _build_option_groups(self, rows, candidate_columns):
        option_groups = []
        for column in candidate_columns:
            options = set()
            for row in rows:
                value = row["section"] if column == "__section__" else clean_text(row["values"].get(column))
                if value:
                    options.add(self._display_option_value(value))
            option_groups.append(
                {
                    "name": self._display_option_name("Modelo" if column == "__section__" else column),
                    "options": sorted(options, key=self._option_sort_key),
                }
            )

        return option_groups

    def _should_include_section_in_variant_name(self, title, rows):
        section_names = {
            row["section"]
            for row in rows
            if row["section"] and row["section"] != title
        }
        return len(section_names) > 1

    def _candidate_columns(self, rows):
        candidate_columns = []
        for key in rows[0]["values"].keys():
            if key in self.EXCLUDED_OPTION_COLUMNS:
                continue

            unique_values = {
                clean_text(row["values"].get(key))
                for row in rows
                if clean_text(row["values"].get(key))
            }

            if 1 < len(unique_values) <= 12:
                candidate_columns.append(key)

        return candidate_columns

    def _requires_section_option_group(self, rows, candidate_columns):
        section_names = {
            row["section"]
            for row in rows
            if row["section"]
        }
        if len(section_names) <= 1:
            return False

        seen_signatures = set()
        for row in rows:
            signature = tuple(
                clean_text(row["values"].get(column))
                for column in candidate_columns
            )
            if signature in seen_signatures:
                return True
            seen_signatures.add(signature)

        return False

    def _build_variants(self, title, sections):
        rows = []
        for section in sections:
            section_name = clean_text(section.get("section"))
            for row in section["rows"]:
                rows.append(
                    {
                        "section": section_name,
                        "values": row,
                    }
                )

        if not rows:
            return [], []

        candidate_columns = self._candidate_columns(rows)
        include_section_as_option = self._requires_section_option_group(rows, candidate_columns)
        if include_section_as_option:
            candidate_columns = candidate_columns + ["__section__"]
        option_groups = self._build_option_groups(rows, candidate_columns)
        include_section_in_name = self._should_include_section_in_variant_name(title, rows)

        variants = []
        for row in rows:
            values = row["values"]
            ref = clean_text(values.get("Ref"))
            if not ref:
                continue

            section_name = row["section"] or title
            option_values = {}
            for column in candidate_columns:
                value = section_name if column == "__section__" else clean_text(values.get(column))
                if value:
                    option_values[self._display_option_name("Modelo" if column == "__section__" else column)] = self._display_option_value(value)

            display_title = self._translate_text(title)
            variant_suffix = self._variant_display_suffix(display_title, option_values)
            variant_name = display_title
            if variant_suffix:
                variant_name = f"{display_title} {variant_suffix}"
            elif include_section_in_name and section_name and section_name != title:
                variant_name = f"{display_title} {self._translate_text(section_name)}"

            variants.append(
                {
                    "name": variant_name,
                    "sku": ref,
                    "price": 0,
                    "options": option_values,
                }
            )

        return option_groups, variants

    def _sections_from_records(self, records):
        grouped_sections = {}
        for record in records:
            section_name = clean_text(record.get("section"))
            grouped_sections.setdefault(section_name, []).append(record["values"])

        return [
            {"section": section_name, "rows": rows}
            for section_name, rows in grouped_sections.items()
        ]

    def _record_images(self, records, parser, url):
        images = []
        for record in records:
            images.extend(record.get("images") or [])
        return list(dict.fromkeys(images)) or parser.images(url)

    def _build_catalog_products(self, title, records, parser, url):
        labels = parser.breadcrumb_labels() or ["ecolux"]
        grouped = {}

        for record in records:
            section_name = clean_text(record.get("section")) or title
            description = self._description_value(record["values"])
            ref = clean_text(record.get("sku"))
            if not description or not ref:
                continue

            group_key = (section_name, self._normalize_description_key(description))
            grouped.setdefault(
                group_key,
                {
                    "section": section_name,
                    "description": description,
                    "records": [],
                },
            )
            grouped[group_key]["records"].append(record)

        products = []
        for group in grouped.values():
            section_name = group["section"]
            description = group["description"]
            product_name = self._translate_text(description)
            product_slug = slugify(f"{title} {section_name} {description}")
            product_labels = labels + ([self._translate_text(section_name)] if section_name and section_name != title else [])
            group_records = group["records"]
            group_sections = [{"section": section_name, "rows": [record["values"] for record in group_records]}]
            option_groups, variants = self._build_variants(product_name, group_sections)
            group_images = self._record_images(group_records, parser, url)

            if len(group_records) == 1:
                single_ref = clean_text(group_records[0]["values"].get("Ref"))
                products.append(
                    self._build_single_variant_product(
                        name=product_name,
                        description=description,
                        ref=single_ref,
                        labels=product_labels,
                        images=group_images,
                        url=url,
                        slug=product_slug,
                    )
                )
                continue

            first_sku = variants[0]["sku"] if variants else clean_text(group_records[0]["values"].get("Ref"))
            if not variants and first_sku:
                products.append(
                    self._build_single_variant_product(
                        name=product_name,
                        description=description,
                        ref=first_sku,
                        labels=product_labels,
                        images=group_images,
                        url=url,
                        slug=product_slug,
                    )
                )
                continue

            products.append(
                build_scraped_product(
                    name=product_name,
                    slug=product_slug,
                    description=self._translate_text(description),
                    description_full=None,
                    sku=first_sku,
                    images=group_images,
                    labels=self._display_labels(product_labels),
                    option_groups=option_groups,
                    variants=variants,
                    source_url=url,
                    supplier="ecolux",
                )
            )

        return products

    def extract(self, html, url):
        parser = EcoluxParser(html)
        title = parser.page_title()

        if not title:
            return None

        records = parser.sku_records(url)
        if self._is_catalog_page(records):
            return self._build_catalog_products(title, records, parser, url)

        sections = self._sections_from_records(records) if records else parser.technical_sections()
        option_groups, variants = self._build_variants(title, sections)
        first_sku = variants[0]["sku"] if variants else None

        return build_scraped_product(
            name=self._translate_text(title),
            description=self._extract_description(parser),
            description_full=None,
            sku=first_sku,
            images=self._record_images(records, parser, url),
            labels=self._display_labels(parser.breadcrumb_labels() or ["ecolux"]),
            option_groups=option_groups,
            variants=variants,
            source_url=url,
            supplier="ecolux",
        )
