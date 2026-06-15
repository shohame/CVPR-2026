import json
import re
from html import unescape
from pathlib import Path

from Parer_Utils.Paper_Dataset import Paper_Dataset

class Abstract_Reader(Paper_Dataset):
    def __init__(self):
        super().__init__()


    def read_abstract(self, index):
        paper_prop = self.get_paper_properties(index)
        html_path = Path(paper_prop['download_paths']['html'])
        if not html_path.exists():
            raise FileNotFoundError(f"HTML file not found: {html_path}")

        html_text = html_path.read_text(encoding="utf-8", errors="replace")
        match = re.search(r'<div id="abstract">\s*(.*?)\s*</div>', html_text, flags=re.IGNORECASE | re.DOTALL)
        if not match:
            raise ValueError(f"Abstract section not found in: {html_path}")

        abstract_html = match.group(1)
        abstract_no_tags = re.sub(r"<[^>]+>", " ", abstract_html)
        abstract_text = unescape(re.sub(r"\s+", " ", abstract_no_tags)).strip()
        return abstract_text



if __name__ == "__main__":
    abs_reader = Abstract_Reader()
    N = abs_reader.get_number_of_papers()
    abs_str = abs_reader.read_abstract(0)
    print(abs_str)


 #   for index in range(N):
