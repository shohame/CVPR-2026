import json
from pathlib import Path

import requests

JSON_FILE_PATH = 'cvpr-constellation.github.io-main/papers.json'
URL_BASE = 'https://openaccess.thecvf.com/content/CVPR2026/'
URL_HTML = 'html/'
URL_PDF = 'papers/'
URL_SUFFIX = '_CVPR_2026_paper.'
DOWNLOAD_PATH = './downloads/papers/'


class Download_Papers:
    def __init__(self):
        self._all_papers_file_ath = JSON_FILE_PATH
        self._url_base = URL_BASE
        self._url_suffix = URL_SUFFIX
        self._url_html = URL_HTML
        self._url_pdf = URL_PDF
        self._download_path = DOWNLOAD_PATH

        with open(self._all_papers_file_ath, encoding="utf-8") as f:
            self._all_papers = json.load(f)
        print(f'Number of papers: {len(self._all_papers)}')

    def get_number_of_papers(self):
        return len(self._all_papers)

    def download_paper(self, index):
        paper = self._all_papers[index]
        paper_name = paper[1]
        paper_url = self._url_base + self._url_pdf + paper_name + self._url_suffix + 'pdf'
        html_url = self._url_base + self._url_html + paper_name + self._url_suffix + 'html'

        paper_download_path = self._download_path + self._url_pdf + paper_name + self._url_suffix + 'pdf'
        html_download_path = self._download_path + self._url_html + paper_name + self._url_suffix + 'html'

        Path(paper_download_path).parent.mkdir(parents=True, exist_ok=True)
        Path(html_download_path).parent.mkdir(parents=True, exist_ok=True)

        html_path = Path(html_download_path)
        if not html_path.exists():
            html_response = requests.get(html_url, timeout=30)
            html_response.raise_for_status()
            with open(html_download_path, "w", encoding="utf-8") as f:
                f.write(html_response.text)
            print(f"Saved {html_download_path}")

        else:
            print(f"Skipped existing {html_download_path}")

        paper_path = Path(paper_download_path)
        if not paper_path.exists():
            paper_response = requests.get(paper_url, timeout=30)
            paper_response.raise_for_status()
            with open(paper_download_path, "wb") as f:
                f.write(paper_response.content)
            print(f"Saved {paper_download_path}")

        else:
            print(f"Skipped existing {paper_download_path}")



if __name__ == "__main__":
    downloader = Download_Papers()
    N = downloader.get_number_of_papers()
    for index in range(N):
        downloader.download_paper(index)  # Download the first paper as an example
