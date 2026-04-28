import re
from urllib.parse import urljoin, urlparse

from scrapers.base import BaseHtmlParser, clean_text, unique_strings


class AronlightParser(BaseHtmlParser):
    SKU_PATTERN = re.compile(r"ILAR-\d+")
    BLOCKED_IMAGE_FRAGMENTS = {
        "logo",
        "recuperarportugal",
        "cookie",
        "flag",
        "social",
        "icon",
    }
    STOP_TEXTS = {
        "ABOUT US",
        "LINK",
        "SEGMENTS",
        "CONTACT US",
        "SOCIAL MEDIA",
        "SWITCH THE LANGUAGE",
        "PURCHASE",
    }

    def __init__(self, html):
        super().__init__(html)
        # Aronlight pages often force us to scan the same DOM regions several
        # times while extracting title, description, links, and tables. These
        # small caches keep the scraper readable without repeating that cost.
        self._page_title_cache = None
        self._page_title_loaded = False
        self._link_entries_cache = {}
        self._content_wrappers_cache = None

    def all_links(self, base_url):
        return sorted({entry["href"] for entry in self.link_entries(base_url)})

    def link_entries(self, base_url):
        if base_url in self._link_entries_cache:
            return self._link_entries_cache[base_url]

        entries = []
        for anchor in self.soup.find_all("a", href=True):
            href = urljoin(base_url, anchor["href"])
            text = clean_text(anchor.get_text(" ", strip=True))
            title = clean_text(anchor.get("title"))
            entries.append(
                {
                    "href": href,
                    "text": text,
                    "title": title,
                }
            )
        self._link_entries_cache[base_url] = entries
        return entries

    def page_title(self):
        if self._page_title_loaded:
            return self._page_title_cache

        for selector in ("h1", "h2", "h3", "h4"):
            for element in self.select(selector):
                text = clean_text(element.get_text(" ", strip=True))
                if not text or text.upper() in self.STOP_TEXTS:
                    continue
                self._page_title_cache = text
                self._page_title_loaded = True
                return text

        self._page_title_loaded = True
        return None

    def breadcrumb_labels(self):
        labels = []
        for element in self.select("li, .breadcrumbs a, .breadcrumb a"):
            text = clean_text(element.get_text(" ", strip=True))
            if not text:
                continue
            if text.upper() in {"HOME", self.page_title() or ""}:
                continue
            labels.append(text)
        return unique_strings(labels)

    def description(self):
        wrapper = self._description_wrapper()
        if wrapper is not None:
            # Marketing copy normally lives in the first plain wrapper, while
            # tabbed technical content is handled separately as description_full.
            paragraph = wrapper.find("p")
            if paragraph:
                text = clean_text(paragraph.get_text(" ", strip=True))
                if text:
                    return text

            text = clean_text(wrapper.get_text(" ", strip=True))
            if text:
                return text

        blocks = self.content_blocks()
        return blocks[0]["text"] if blocks else None

    def description_full(self):
        wrapper = self._description_full_wrapper()
        if wrapper is not None:
            return str(wrapper)

        blocks = self.content_blocks()
        if len(blocks) < 2:
            return None
        return blocks[1]["html"]

    def _title_anchor(self):
        return self.select_one("h4") or self.select_one("h1")

    def _content_wrappers(self):
        if self._content_wrappers_cache is not None:
            return self._content_wrappers_cache

        title_element = self._title_anchor()
        if not title_element:
            return []

        wrappers = []
        seen = set()
        for element in title_element.find_all_next(["div", "section"]):
            if element.name in {"h1", "h2", "h3", "h4"}:
                break

            classes = set(element.get("class", []))
            if "wpb_wrapper" not in classes:
                continue

            element_id = id(element)
            if element_id in seen:
                continue
            seen.add(element_id)
            wrappers.append(element)

        self._content_wrappers_cache = wrappers
        return wrappers

    def _description_wrapper(self):
        for wrapper in self._content_wrappers():
            classes = set(wrapper.get("class", []))
            if "rt-wrapper" in classes or wrapper.select_one(".rt_tabs"):
                continue
            if wrapper.find("p") or wrapper.select_one("table"):
                return wrapper
        return None

    def _description_full_wrapper(self):
        for wrapper in self._content_wrappers():
            classes = set(wrapper.get("class", []))
            # The richer Aronlight technical blocks usually live inside
            # rt-wrapper / rt_tabs containers, so we preserve that HTML whole.
            if "rt-wrapper" in classes or wrapper.select_one(".rt_tabs"):
                return wrapper
        return None

    def content_blocks(self):
        title_element = self._title_anchor()
        if not title_element:
            return []

        blocks = []
        for sibling in title_element.next_siblings:
            sibling_name = getattr(sibling, "name", None)
            if sibling_name in {"h1", "h2", "h3", "h4"}:
                break

            if sibling_name is None:
                continue

            strings = getattr(sibling, "stripped_strings", None)
            if not strings:
                continue

            text = clean_text(" ".join(strings))
            if not text or text.upper() in self.STOP_TEXTS:
                continue

            blocks.append(
                {
                    "text": text,
                    "html": str(sibling),
                }
            )

        return blocks

    def images(self, base_url):
        images = []
        for image in self.soup.find_all("img", src=True):
            src = clean_text(image.get("src"))
            if not src:
                continue

            lowered = src.lower()
            # Aronlight pages include decorative assets such as flags, icons,
            # and social logos. Filtering them here keeps Beevo galleries clean.
            if any(fragment in lowered for fragment in self.BLOCKED_IMAGE_FRAGMENTS):
                continue

            absolute = urljoin(base_url, src)
            parsed = urlparse(absolute)
            if not parsed.path.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
                continue

            images.append(absolute)

        return unique_strings(images)

    def product_tables(self):
        sections = []
        current_heading = None

        for element in self.soup.select("h2, h3, h4, h5, h6, li.tab_title, div.tab_title, table"):
            if element.name != "table":
                # Tab titles like "6 WATTS" act as semantic section headings
                # on Aronlight even though they are not normal heading tags.
                heading = clean_text(element.get_text(" ", strip=True))
                if heading and heading.upper() not in self.STOP_TEXTS:
                    current_heading = heading
                continue

            parent_classes = " ".join(element.parent.get("class", [])) if element.parent else ""
            # Summary/specification tables in the top content block are useful
            # for descriptions, but they are not sellable variant matrices.
            if "table-responsive" in parent_classes and current_heading == self.page_title():
                continue

            rows = []
            for row in element.select("tr"):
                cells = row.find_all(["th", "td"])
                values = [clean_text(cell.get_text(" ", strip=True)) for cell in cells]
                values = [value for value in values if value]
                if values:
                    rows.append(values)

            if rows:
                sections.append({"section": current_heading, "rows": rows})

        return sections
