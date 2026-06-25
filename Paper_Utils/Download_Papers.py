import json
from pathlib import Path
from tqdm import tqdm
import requests
from Paper_Dataset import Paper_Dataset

class Download_Papers(Paper_Dataset):

    def __init__(self):
        super().__init__()


    def download_paper(self, index):

        paper_prop = self.get_paper_properties(index)
        paper_url = paper_prop['urls']['pdf']
        html_url = paper_prop['urls']['html']
        paper_download_path = paper_prop['download_paths']['pdf']
        html_download_path = paper_prop['download_paths']['html']

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
    for index in tqdm(range(N)):
        downloader.download_paper(index)  # Download the first paper as an example
