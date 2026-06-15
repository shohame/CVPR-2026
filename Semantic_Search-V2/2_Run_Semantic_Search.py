import numpy as np
import torch
import os
from sentence_transformers import SentenceTransformer, util
from Parer_Utils.Paper_Dataset import Paper_Dataset


class Run_Semantic_Search(Paper_Dataset):
    def __init__(self):
        super().__init__()
        MODEL_PATH = "./my_local_model"
        VECTORS_PATH = "cvpr2026_semantic_vectors.npy"

        if not os.path.exists(MODEL_PATH) or not os.path.exists(VECTORS_PATH):
            raise FileNotFoundError("Missing local model files or pre-computed vectors matrix.")

        print("Loading upgraded local embedding model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")

        self._model = SentenceTransformer(MODEL_PATH, device=device)
        print("Loading dataset and semantic matrix...")
        self._all_vectors = np.load(VECTORS_PATH)

    def get_semantic_search_top_indices(self, query_text, top_k=5):
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
        print("\nTop search results (Upgraded Model):")
        print("=" * 60)
        for rank, idx in enumerate(indices, start=1):
            paper_prop = self.get_paper_properties(idx)
            title = paper_prop.get('paper_name', 'Unknown Title')
            print(f"Rank {rank} | Index: {idx} - Title: {title}")


if __name__ == "__main__":
    searcher = Run_Semantic_Search()

    # Try searching with complex domain jargon
    query = "unsupervised domain adaptation for autonomous drone detection in thermal infrared infrared videos"
    query = "Sound reconstruction via laser and camera"
    top_indices = searcher.get_semantic_search_top_indices(query, top_k=50)
    searcher.print_indices(top_indices)