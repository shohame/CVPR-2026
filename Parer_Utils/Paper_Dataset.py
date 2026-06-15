import json
from pathlib import Path
import sys

CURRENT_PATH = Path(__file__).resolve().parent
JSON_FILE_PATH = CURRENT_PATH.as_posix() + '/papers_all.json'
URL_BASE = 'https://openaccess.thecvf.com/content/CVPR2026/'
URL_HTML = 'html/'
URL_PDF = 'papers/'
URL_SUFFIX = '_CVPR_2026_paper.'
DOWNLOAD_PATH = (CURRENT_PATH / 'downloads' / 'papers').as_posix() + '/'

class Paper_Dataset:
    def __init__(self):
        self._all_papers_json = JSON_FILE_PATH
        self._url_base = URL_BASE
        self._url_suffix = URL_SUFFIX
        self._url_html = URL_HTML
        self._url_pdf = URL_PDF
        self._download_path = DOWNLOAD_PATH

        with open(self._all_papers_json, encoding="utf-8") as f:
            self._all_papers = json.load(f)

        # Only print if not running in Streamlit
        if "streamlit" not in sys.modules:
            print(f'Number of papers: {len(self._all_papers)}')

    def get_number_of_papers(self):
        return len(self._all_papers)

    def get_paper_properties(self, index):
        paper = self._all_papers[index]
        paper_name = paper[1]
        pdf_url = self._url_base + self._url_pdf + paper_name + self._url_suffix + 'pdf'
        html_url = self._url_base + self._url_html + paper_name + self._url_suffix + 'html'

        pdf_download_path = self._download_path + self._url_pdf + paper_name + self._url_suffix + 'pdf'
        html_download_path = self._download_path + self._url_html + paper_name + self._url_suffix + 'html'

        ret = { 'paper_name': paper_name,
                'urls':
                   {'pdf': pdf_url,
                    'html': html_url
                    },
               'download_paths':
                   {'pdf': pdf_download_path,
                    'html': html_download_path
                    }
               }
        return ret




if __name__ == "__main__":
    dataset = Paper_Dataset()
    N = dataset.get_number_of_papers()
    print(f"Total papers: {N}")
    paper_props = dataset.get_paper_properties(0)
    print(paper_props)