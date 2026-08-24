import numpy as np
import torch
import os
import sys
from pathlib import Path
from sentence_transformers import SentenceTransformer, util



# Add parent directory to path so we can import Paper_Utils
parent_dir = str(Path(__file__).parent.parent)
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

from Paper_Utils.Abstract_Reader import Abstract_Reader


class Run_Semantic_Search(Abstract_Reader):
    def __init__(self, device=None):
        super().__init__()
        SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
        MODEL_PATH = os.path.join(SCRIPT_DIR, "my_local_model")
        VECTORS_PATH = os.path.join(SCRIPT_DIR, "cvpr2026_semantic_vectors.npy")

        if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORS_PATH):
            raise FileNotFoundError("Missing local model files or pre-computed vectors matrix.")

        # Only print if not running in Streamlit
        is_streamlit = "streamlit" in sys.modules

        if not is_streamlit:
            print("Loading upgraded local embedding model...")
        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"

        if not is_streamlit:
            print(f"Using device: {device}")

        self._model = SentenceTransformer(MODEL_PATH, device=device)
        if not is_streamlit:
            print("Loading dataset and semantic matrix...")
        self._all_vectors = np.load(VECTORS_PATH)

    def get_semantic_search_top_indices(self, query_text, top_k=5):
        is_streamlit = "streamlit" in sys.modules
        if not is_streamlit:
            print(f"\nProcessing search query: '{query_text}'")

        # BAAI BGE models do not strictly require task prefixes in newer SentenceTransformer releases,
        # but normalizing input text ensures stable cosine distances.
        query_text_normalized = query_text.strip()

        # Encode user query
        query_vector = self._model.encode(query_text_normalized, convert_to_numpy=True)

        # Compute Cosine Similarity between 1024-dimension arrays
        cosine_scores = util.cos_sim(query_vector, self._all_vectors)[0]

        # Extract top scoring positions
        top_results_indices = np.argsort(cosine_scores.numpy())[-top_k:][::-1]

        return top_results_indices

    def print_indices(self, indices):
        is_streamlit = "streamlit" in sys.modules
        if not is_streamlit:
            print("\nTop search results (Upgraded Model):")
            print("=" * 60)
        for rank, idx in enumerate(indices, start=1):
            paper_prop = self.get_paper_properties(idx)
            title = paper_prop.get('paper_name', 'Unknown Title')
            if not is_streamlit:
                print(f"Rank {rank} | Index: {idx} - Title: {title}")


if __name__ == "__main__":
    searcher = Run_Semantic_Search()

    # Try searching with complex domain jargon
    query = "unsupervised domain adaptation for autonomous drone detection in thermal infrared infrared videos"
    query = "Sound reconstruction via laser and camera"
    query = "פעפוע"
    top_indices = searcher.get_semantic_search_top_indices(query, top_k=50)
    searcher.print_indices(top_indices)