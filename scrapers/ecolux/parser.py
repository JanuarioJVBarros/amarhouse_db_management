from urllib.parse import urljoin
import re

from scrapers.base import BaseHtmlParser, clean_text


class EcoluxParser(BaseHtmlParser):
    SKU_PATTERN = re.compile(r"EC-\d+")
    SKIP_TITLES = {
        "INICIO",
        "PRODUCTOS",
        "DATOS TÉCNICOS",
        "GRÁFICOS Y MEDIDAS",
        "DESCARGA DE ARCHIVOS",
        "COMPÁRTELO!",
    }

    def all_links(self, base_url):
        links = set()

        for anchor in self.soup.find_all("a", href=True):
            links.add(urljoin(base_url, anchor["href"]))

        return links

    def page_title(self):
        for selector in ("h1", "h2", "h3"):
            for element in self.select(selector):
                text = element.get_text(" ", strip=True)
                if not text:
                    continue
                if text.upper() in self.SKIP_TITLES:
                    continue
                return text
        return None

    def breadcrumb_labels(self):
        labels = []

        for element in self.select("li, .breadcrumb a, .fusion-breadcrumbs a"):
            text = element.get_text(" ", strip=True)
            if not text:
                continue
            if text.upper() in {"INICIO", "PRODUCTOS"}:
                continue
            labels.append(text)

        return labels

    def images(self, base_url):
        return [entry["url"] for entry in self.image_entries(base_url)]

    def _is_blocked_image(self, src):
        blocked_fragments = {
            "logo",
            "banner_footer",
            "sellos",
            "kit-digital",
            "epistar",
            "red-es",
        }
        lowered = src.lower()
        return any(fragment in lowered for fragment in blocked_fragments)

    def _extract_skus(self, text):
        if not text:
            return []
        return sorted(set(self.SKU_PATTERN.findall(text)))

    def image_entries(self, base_url):
        entries = []
        current_heading = None

        for element in self.soup.select("h2, h3, h4, img"):
            if element.name in {"h2", "h3", "h4"}:
                heading = clean_text(element.get_text(" ", strip=True))
                if heading:
                    current_heading = heading
                continue

            src = clean_text(element.get("src"))
            if not src or self._is_blocked_image(src):
                continue

            alt_text = clean_text(
                " ".join(
                    filter(
                        None,
                        [
                            element.get("alt"),
                            element.get("title"),
                            element.get("aria-label"),
                        ],
                    )
                )
            )
            entries.append(
                {
                    "url": urljoin(base_url, src),
                    "alt": alt_text,
                    "section": current_heading,
                    "skus": self._extract_skus(alt_text),
                }
            )

        return entries

    def _normalize_header(self, value):
        text = clean_text(value or "")
        if not text:
            return None

        normalized = text.rstrip(":").rstrip(".")
        if normalized.lower() in {"ref", "referencia", "referência"}:
            return "Ref"

        return normalized

    def _is_ref_header(self, value):
        return self._normalize_header(value) == "Ref"

    def _extract_table_rows(self, element):
        rows = []
        for row in element.select("tr"):
            cells = row.find_all(["th", "td"])
            values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
            cleaned = [value for value in values if value]
            if cleaned:
                rows.append(cleaned)
        return rows

    def _parse_text_section_block(self, lines):
        header_index = None
        headers = None

        for index, line in enumerate(lines):
            if not line:
                continue
            normalized = re.sub(r"\s+", " ", line).strip()
            if not normalized.lower().startswith("ref "):
                continue

            parts = re.split(r"\s{2,}", normalized)
            if len(parts) == 1:
                parts = normalized.split()

            normalized_headers = [self._normalize_header(part) for part in parts]
            if any(self._is_ref_header(value) for value in normalized_headers):
                header_index = index
                headers = self._merge_header_tokens(normalized_headers)
                break

        if header_index is None or not headers:
            return []

        rows = []
        for line in lines[header_index + 1:]:
            if not line or not re.match(r"^EC-\d+", line):
                continue

            normalized = re.sub(r"\s+", " ", line).strip()
            if len(headers) == 3:
                match = re.match(r"^(EC-\d+)\s+(.+?)\s+([^\s]+)$", normalized)
                if not match:
                    continue
                values = [match.group(1), match.group(2), match.group(3)]
            else:
                values = normalized.split(maxsplit=len(headers) - 1)
                if len(values) != len(headers):
                    continue

            row_map = {
                header: clean_text(value)
                for header, value in zip(headers, values)
                if header
            }
            if row_map.get("Ref"):
                rows.append(row_map)

        return rows

    def _merge_header_tokens(self, headers):
        merged = []
        index = 0

        while index < len(headers):
            current = headers[index]
            next_value = headers[index + 1] if index + 1 < len(headers) else None

            if current == "Temp" and next_value == "(K)":
                merged.append("Temp (K)")
                index += 2
                continue

            merged.append(current)
            index += 1

        return merged

    def _text_sections(self):
        sections = []

        for heading in self.soup.select("h2, h3, h4"):
            heading_text = clean_text(heading.get_text(" ", strip=True))
            if not heading_text:
                continue

            lines = []
            for sibling in heading.next_siblings:
                sibling_name = getattr(sibling, "name", None)
                if sibling_name in {"h2", "h3", "h4"}:
                    break

                stripped_strings = getattr(sibling, "stripped_strings", None)
                if not stripped_strings:
                    continue

                for value in stripped_strings:
                    text = clean_text(value)
                    if text:
                        lines.append(text)

            rows = self._parse_text_section_block(lines)
            if rows:
                sections.append({
                    "section": heading_text,
                    "rows": rows,
                })

        return sections

    def technical_sections(self):
        sections = []
        current_heading = None

        for element in self.soup.select("h2, h3, h4, table"):
            if element.name in {"h2", "h3", "h4"}:
                heading = element.get_text(" ", strip=True)
                if heading:
                    current_heading = heading
                continue

            table_rows = self._extract_table_rows(element)
            if not table_rows:
                continue

            header_index = None
            headers = None
            for index, row_values in enumerate(table_rows):
                normalized_headers = [self._normalize_header(value) for value in row_values]
                if any(self._is_ref_header(value) for value in normalized_headers):
                    header_index = index
                    headers = normalized_headers
                    break

            if header_index is None or not headers:
                continue

            rows = []
            for row_values in table_rows[header_index + 1:]:
                if len(row_values) < len(headers):
                    row_values = row_values + [None] * (len(headers) - len(row_values))
                elif len(row_values) > len(headers):
                    row_values = row_values[:len(headers)]

                if any(self._is_ref_header(value) for value in row_values):
                    continue

                row_map = {
                    header: clean_text(value)
                    for header, value in zip(headers, row_values)
                    if header
                }
                if row_map.get("Ref"):
                    rows.append(row_map)

            if rows:
                sections.append({
                    "section": current_heading,
                    "rows": rows,
                })

        if not sections:
            return self._text_sections()

        text_sections = self._text_sections()
        seen_sections = {
            (
                section.get("section"),
                tuple(row.get("Ref") for row in section.get("rows", [])),
            )
            for section in sections
        }

        for section in text_sections:
            section_key = (
                section.get("section"),
                tuple(row.get("Ref") for row in section.get("rows", [])),
            )
            if section_key in seen_sections:
                continue
            sections.append(section)

        return sections

    def sku_records(self, base_url):
        image_entries = self.image_entries(base_url)
        section_images = {}
        sku_images = {}

        for entry in image_entries:
            section_images.setdefault(entry["section"], []).append(entry["url"])
            for sku in entry["skus"]:
                sku_images.setdefault(sku, []).append(entry["url"])

        records = []
        for section in self.technical_sections():
            section_name = clean_text(section.get("section"))
            for row in section.get("rows", []):
                sku = clean_text(row.get("Ref"))
                if not sku:
                    continue

                images = sku_images.get(sku) or section_images.get(section_name) or []
                records.append(
                    {
                        "section": section_name,
                        "sku": sku,
                        "values": row,
                        "images": list(dict.fromkeys(images)),
                    }
                )

        return records
