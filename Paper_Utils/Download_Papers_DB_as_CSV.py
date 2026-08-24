from __future__ import annotations

import argparse
import csv
import sys
import time
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urljoin, urlsplit
from urllib.request import Request, urlopen
from tqdm.auto import tqdm


DEFAULT_LIST_URL = "https://openaccess.thecvf.com/CVPR2026?day=all"
DEFAULT_OUTPUT = Path("cvpr2026_Main_Conference.csv")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0 Safari/537.36"
)
RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}
VOID_ELEMENTS = {
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
}


def normalize_text(value: str) -> str:
    """Collapse HTML whitespace into normal single spaces."""
    return " ".join(value.split())


def get_attributes(attributes: list[tuple[str, str | None]]) -> dict[str, str]:
    """Convert HTMLParser attributes to a convenient dictionary."""
    return {name.lower(): value or "" for name, value in attributes}


class PaperListParser(HTMLParser):
    """Parse paper links from a CVF conference listing page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.primary_links: list[tuple[str, str]] = []
        self.fallback_links: list[tuple[str, str]] = []
        self._in_paper_title = False
        self._current_href: str | None = None
        self._current_text: list[str] = []
        self._current_is_primary = False

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        attrs = get_attributes(attributes)

        if tag.lower() == "dt":
            classes = attrs.get("class", "").split()
            self._in_paper_title = "ptitle" in classes

        if tag.lower() == "a" and self._current_href is None:
            href = attrs.get("href", "").strip()
            if href:
                self._current_href = href
                self._current_text = []
                self._current_is_primary = self._in_paper_title

    def handle_data(self, data: str) -> None:
        if self._current_href is not None:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "a" and self._current_href is not None:
            title = normalize_text("".join(self._current_text))
            href = self._current_href
            if title:
                if self._current_is_primary:
                    self.primary_links.append((title, href))
                elif "/html/" in href and href.endswith("_paper.html"):
                    self.fallback_links.append((title, href))

            self._current_href = None
            self._current_text = []
            self._current_is_primary = False

        if tag == "dt":
            self._in_paper_title = False

    @property
    def links(self) -> list[tuple[str, str]]:
        return self.primary_links or self.fallback_links


class PaperPageParser(HTMLParser):
    """Parse the title, abstract, and PDF links from one CVF paper page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.abstract_parts: list[str] = []
        self.pdf_links: list[tuple[str, str]] = []
        self._title_depth = 0
        self._abstract_depth = 0
        self._current_href: str | None = None
        self._current_link_text: list[str] = []

    def handle_starttag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
    ) -> None:
        attrs = get_attributes(attributes)
        tag = tag.lower()

        if self._title_depth:
            if tag not in VOID_ELEMENTS:
                self._title_depth += 1
        elif tag == "h1":
            self._title_depth = 1

        if self._abstract_depth:
            if tag not in VOID_ELEMENTS:
                self._abstract_depth += 1
        elif attrs.get("id", "").lower() == "abstract":
            self._abstract_depth = 1

        if tag == "br":
            if self._title_depth:
                self.title_parts.append(" ")
            if self._abstract_depth:
                self.abstract_parts.append(" ")

        if tag == "a" and self._current_href is None:
            href = attrs.get("href", "").strip()
            if href:
                self._current_href = href
                self._current_link_text = []

    def handle_startendtag(
        self,
        tag: str,
        attributes: list[tuple[str, str | None]],
        ) -> None:
        # Self-closing tags do not change capture depth.
        if tag.lower() == "br":
            if self._title_depth:
                self.title_parts.append(" ")
            if self._abstract_depth:
                self.abstract_parts.append(" ")

    def handle_data(self, data: str) -> None:
        if self._title_depth:
            self.title_parts.append(data)
        if self._abstract_depth:
            self.abstract_parts.append(data)
        if self._current_href is not None:
            self._current_link_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == "a" and self._current_href is not None:
            path = urlsplit(self._current_href).path.lower()
            if path.endswith(".pdf"):
                text = normalize_text("".join(self._current_link_text))
                self.pdf_links.append((text, self._current_href))
            self._current_href = None
            self._current_link_text = []

        if self._title_depth:
            self._title_depth -= 1
        if self._abstract_depth:
            self._abstract_depth -= 1


def fetch_html(url: str, timeout: float, attempts: int = 4) -> str:
    """Download an HTML page, retrying temporary network failures."""
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )

    last_error: HTTPError | URLError | None = None
    for attempt in range(attempts):
        try:
            with urlopen(request, timeout=timeout) as response:
                encoding = response.headers.get_content_charset() or "utf-8"
                return response.read().decode(encoding, errors="replace")
        except HTTPError as error:
            last_error = error
            if error.code not in RETRYABLE_HTTP_CODES:
                raise
        except URLError as error:
            last_error = error

        if attempt + 1 < attempts:
            time.sleep(0.8 * (2**attempt))

    if last_error is None:
        raise RuntimeError(f"Failed to download {url}")
    raise last_error


def iter_paper_links(html: str, list_url: str) -> Iterable[tuple[str, str]]:
    """Yield unique (title, paper-page URL) pairs from a CVF listing page."""
    parser = PaperListParser()
    parser.feed(html)
    parser.close()

    seen_urls: set[str] = set()
    for title, href in parser.links:
        paper_url = urljoin(list_url, href)
        if paper_url in seen_urls:
            continue
        seen_urls.add(paper_url)
        yield title, paper_url


def find_pdf_url(parser: PaperPageParser, paper_url: str) -> str:
    """Return the most likely main-paper PDF URL, or an empty string."""
    candidates: list[tuple[int, str]] = []

    for link_text, href in parser.pdf_links:
        path = urlsplit(href).path.lower()
        text = link_text.lower()
        score = 0
        if path.endswith("_paper.pdf"):
            score += 100
        if text in {"pdf", "paper", "[pdf]"}:
            score += 20
        if "/papers/" in path:
            score += 10
        if "supp" in path or "supp" in text:
            score -= 100
        candidates.append((score, urljoin(paper_url, href)))

    if not candidates:
        return ""
    return max(candidates, key=lambda item: item[0])[1]


def parse_paper_page(
    html: str,
    paper_url: str,
    listing_title: str,
) -> dict[str, str]:
    """Extract the requested fields from one CVF paper page."""
    parser = PaperPageParser()
    parser.feed(html)
    parser.close()

    page_title = normalize_text("".join(parser.title_parts))
    abstract = normalize_text("".join(parser.abstract_parts))
    pdf_url = find_pdf_url(parser, paper_url)
    pdf_file_name = (
        unquote(PurePosixPath(urlsplit(pdf_url).path).name) if pdf_url else ""
    )

    return {
        "Title": page_title or listing_title,
        "Abstract": abstract,
        "PDF file name": pdf_file_name,
    }


def export_papers(
    list_url: str,
    output_path: Path,
    delay: float,
    timeout: float,
) -> tuple[int, int]:
    """Scrape all papers and write the requested CSV file."""
    list_html = fetch_html(list_url, timeout)
    papers = list(iter_paper_links(list_html, list_url))

    if not papers:
        raise RuntimeError(f"No paper links were found on {list_url}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    failed = 0

    # utf-8-sig lets Microsoft Excel recognize UTF-8 automatically.
    with output_path.open("w", newline="", encoding="utf-8-sig") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=("Title", "Abstract", "PDF file name"),
        )
        writer.writeheader()

        for index, (title, paper_url) in tqdm(enumerate(papers, start=1), total=len(papers), desc="Scraping papers"):
            # print(f"[{index}/{len(papers)}] {title}") # Remove this line as tqdm handles progress
            try:
                paper_html = fetch_html(paper_url, timeout)
                row = parse_paper_page(paper_html, paper_url, title)
            except (HTTPError, URLError) as error:
                failed += 1
                print(f"  Warning: could not read {paper_url}: {error}", file=sys.stderr)
                row = {
                    "Title": title,
                    "Abstract": "",
                    "PDF file name": "",
                }

            writer.writerow(row)

            if delay > 0 and index < len(papers):
                time.sleep(delay)

    return len(papers), failed


def parse_args(args_list: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Export papers from a CVF conference listing page to CSV."
    )
    parser.add_argument(
        "--url",
        default=DEFAULT_LIST_URL,
        help=f"CVF listing URL (default: {DEFAULT_LIST_URL})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Output CSV path (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Delay in seconds between paper requests (default: 0.15)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds (default: 30)",
    )
    args = parser.parse_args(args_list)

    if args.delay < 0:
        parser.error("--delay must be non-negative")
    if args.timeout <= 0:
        parser.error("--timeout must be positive")

    return args


def main() -> int:
    args = parse_args([])

    try:
        total, failed = export_papers(
            list_url=args.url,
            output_path=args.output,
            delay=args.delay,
            timeout=args.timeout,
        )
    except (HTTPError, URLError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    print(f"Wrote {total} rows to {args.output}")
    if failed:
        print(f"{failed} paper pages failed; their missing fields were left empty.")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())