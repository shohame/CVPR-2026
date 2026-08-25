import os
import numpy as np
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer

# Importing your project utils
from Paper_Utils.Paper_Dataset import Paper_Dataset

def main():
    MODEL_PATH = "./my_local_model"
    OUTPUT_VECTORS_PATH = "cvpr2026_semantic_vectors.npy"

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Local model directory not found at {MODEL_PATH}. "
            f"Please run script 0 on a connected machine first."
        )

    # Initialize data reader
    print("Initializing Paper Dataset...")
    paper_db = Paper_Dataset()
    num_papers = paper_db.get_number_of_papers()
    print(f"Found {num_papers} papers to process.")

    # Initialize upgraded model
    print(f"Loading semantic embedding model from {MODEL_PATH}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = SentenceTransformer(MODEL_PATH, device=device)

    # Extract text and enrich context (Title + Abstract)
    print("Extracting titles and abstracts...")
    enriched_texts = []

    for idx in tqdm(range(num_papers)):
        # Get title from your existing JSON data mapping
        paper_prop = paper_db.get_paper_properties(idx)
        paper_title = paper_prop["paper_name"]
        abstract_text = paper_prop["abstract"]

        # Strategic improvement: Combine Title and Abstract for a stronger semantic signal
        combined_context = f"Title: {paper_title}. Abstract: {abstract_text}"
        enriched_texts.append(combined_context)

    # Generate semantic embeddings in optimized batches
    print(f"Generating enhanced semantic vectors for {len(enriched_texts)} papers...")
    # BGE-Large has a dimension size of 1024. batch_size can be 32 (or adjusted based on GPU VRAM)
    all_vectors = model.encode(
        enriched_texts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # Save the 1024-dimension matrix to disk
    np.save(OUTPUT_VECTORS_PATH, all_vectors)
    print(f"Success! Enhanced semantic vectors saved to {OUTPUT_VECTORS_PATH}")
    print(f"Matrix shape: {all_vectors.shape} (Papers, 1024 Dimensions)")


if __name__ == "__main__":
    main()