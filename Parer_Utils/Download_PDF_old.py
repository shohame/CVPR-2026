import requests
import os
import urllib.parse
import xml.etree.ElementTree as ET
import re
from pathlib import Path


def load_links_from_file(file_path):
    """Load non-empty links from a text file (one URL per line)."""
    with open(file_path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]




def sanitize_filename(title):
    """Removes illegal characters for saving files on Windows/Mac."""
    clean = re.sub(r'[\\/*?:"<>|]', "", title)
    return clean[:150]  # Limit length so OS doesn't reject it


def get_paper_title(url):
    """Determines the title of the paper based on the URL type."""
    # 1. If it's a search page, extract title from URL query
    if "search/?query=" in url:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        if 'query' in query_params:
            raw_title = query_params['query'][0]
            # Clean up the URL encoding artifacts
            return raw_title.replace('+', ' ').strip()

    # 2. If it's a direct PDF, fetch title using arXiv API
    elif "arxiv.org/pdf/" in url or "arxiv.org/abs/" in url:
        arxiv_id = url.split('/')[-1].replace('.pdf', '')
        api_url = f'http://export.arxiv.org/api/query?id_list={arxiv_id}'
        try:
            response = requests.get(api_url)
            root = ET.fromstring(response.content)
            # Find the title tag in the XML response
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            title_element = root.find('.//atom:entry/atom:title', ns)
            if title_element is not None:
                # Remove newlines that the API sometimes adds
                return title_element.text.strip().replace('\n', ' ')
        except Exception:
            pass  # Fallback to using the ID if the API call fails

        return f"Arxiv_Paper_{arxiv_id}"

    return "Unknown_Document"


def _extract_entry_from_api(api_xml_bytes):
    """Return first arXiv entry element from API XML response."""
    root = ET.fromstring(api_xml_bytes)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    return root.find(".//atom:entry", ns), ns


def _extract_id_from_entry(entry, ns):
    """Extract arXiv id from entry id URL."""
    if entry is None:
        return None
    id_el = entry.find("atom:id", ns)
    if id_el is None or not id_el.text:
        return None
    return id_el.text.rstrip("/").split("/")[-1]


def resolve_pdf_url(url):
    """Resolve arXiv search/abs/pdf URL to direct PDF URL."""
    if "arxiv.org/pdf/" in url:
        if url.endswith(".pdf"):
            return url
        return f"{url}.pdf"

    if "arxiv.org/abs/" in url:
        arxiv_id = url.rstrip("/").split("/")[-1].replace(".pdf", "")
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    if "search/?query=" in url:
        parsed_url = urllib.parse.urlparse(url)
        query_params = urllib.parse.parse_qs(parsed_url.query)
        title_query = query_params.get("query", [None])[0]
        if not title_query:
            return None

        # Query arXiv API by title and use the first hit.
        api_url = (
            "http://export.arxiv.org/api/query?"
            + urllib.parse.urlencode(
                {
                    "search_query": f'ti:"{title_query}"',
                    "start": 0,
                    "max_results": 1,
                }
            )
        )
        response = requests.get(api_url, timeout=20)
        response.raise_for_status()
        entry, ns = _extract_entry_from_api(response.content)
        arxiv_id = _extract_id_from_entry(entry, ns)
        if not arxiv_id:
            return None
        return f"https://arxiv.org/pdf/{arxiv_id}.pdf"

    return None


def Download_PDF(urls_file, output_dir="downloaded_pdfs"):
    links_file = Path(urls_file)
    all_links = load_links_from_file(links_file)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    failed_links = []

    print(f"Starting PDF downloads for {len(all_links)} links...\n")

    for i, link in enumerate(all_links):
        raw_title = get_paper_title(link)
        safe_title = sanitize_filename(raw_title)
        filename = output_path / f"{safe_title}.pdf"
        print(f"[{i + 1}/{len(all_links)}] Downloading: {filename.name}")

        try:
            pdf_url = resolve_pdf_url(link)
            if not pdf_url:
                print("  -> Skipped (could not resolve PDF URL).")
                failed_links.append(link)
                continue

            headers = {"User-Agent": "Mozilla/5.0"}
            response = requests.get(pdf_url, headers=headers, timeout=30)
            response.raise_for_status()

            with open(filename, "wb") as f:
                f.write(response.content)

            print("  -> Saved.")
        except requests.exceptions.RequestException as e:
            print(f"  -> Failed to download. Error: {e}")
            failed_links.append(link)
        except ET.ParseError as e:
            print(f"  -> Failed to parse API response. Error: {e}")
            failed_links.append(link)

    failed_links_file = output_path / "failed_links.txt"
    with open(failed_links_file, "w", encoding="utf-8") as f:
        for failed_link in failed_links:
            f.write(f"{failed_link}\n")

    print(f"Failed links: {len(failed_links)} (saved to {failed_links_file})")

    print(f"\nAll finished! PDFs saved in: {output_path}")


if __name__ == "__main__":
    date_to_dl = 5
   # path_fn = f'downloaded_pdfs/{date_to_dl}'
    path_fn = f'{date_to_dl}'

    links_file = Path(f"{path_fn}.txt")
    Download_PDF(links_file, path_fn)
