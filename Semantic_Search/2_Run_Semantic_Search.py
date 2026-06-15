import numpy as np
import torch
from sentence_transformers import SentenceTransformer, util
from Parer_Utils.Paper_Dataset import Paper_Dataset

class Run_Semantic_Search(Paper_Dataset):
    def __init__(self):
        super().__init__()
        MODEL_PATH = "./my_local_model"
        VECTORS_PATH = "cvpr2026_semantic_vectors.npy"

        print("Loading local embedding model...")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Using device: {device}")
        self._model = SentenceTransformer(MODEL_PATH, device=device)
        print("Loading dataset and semantic matrix...")
        self._all_vectors = np.load(VECTORS_PATH)


    def get_semantic_search_top_indices(self, query_text, top_k=5):
        print(f"\nProcessing search query: '{query_text}'")
        query_vector = self._model.encode(query_text, convert_to_numpy=True)

        # Compute Cosine Similarity between the query vector and all paper vectors
        # This matrix multiplication is extremely fast, even for thousands of papers on a CPU
        cosine_scores = util.cos_sim(query_vector, self._all_vectors)[0]

        top_results_indices = np.argsort(cosine_scores.numpy())[-top_k:][::-1]

        return top_results_indices

    def print_indices(self, indices):
        print("\nTop search results:")
        for rank, idx in enumerate(indices, start=1):
            paper_prop = self.get_paper_properties(idx)
            title = paper_prop['paper_name']
            print(f"{rank}. Paper Index: {idx} - Title: {title}")

if __name__ == "__main__":
    searcher = Run_Semantic_Search()
    query = "What are the latest advancements in object detection for autonomous vehicles?"
    query = "3d & diffusion"
    top_indices = searcher.get_semantic_search_top_indices(query, top_k=5)
    searcher.print_indices(top_indices)