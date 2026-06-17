import os
import numpy as np
import torch
from huggingface_hub.utils import tqdm
from sentence_transformers import SentenceTransformer

# 1. Import your Abstract_Reader class
from Paper_Utils.Abstract_Reader import Abstract_Reader


def main():
    # 2. Path to your locally downloaded model weights (transferred to the air-gapped system)
    # Ensure this directory contains the downloaded 'all-MiniLM-L6-v2' model files
    MODEL_PATH = "./my_local_model"

    if not os.path.exists(MODEL_PATH):
        raise FileNotFoundError(
            f"Local model directory not found at {MODEL_PATH}. "
            f"Please download 'all-MiniLM-L6-v2' on a connected machine using model.save()."
        )

    # 3. Initialize the Abstract_Reader and the local SentenceTransformer
    print("Initializing Abstract Reader...")
    reader = Abstract_Reader()
    num_papers = reader.get_number_of_papers()
    print(f"Found {num_papers} papers to process.")

    print(f"Loading semantic embedding model from {MODEL_PATH}...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device}")
    model = SentenceTransformer(MODEL_PATH, device=device)

    # 4. Extract all abstracts using the Abstract_Reader instance
    print("Extracting abstracts from HTML files...")
    all_abstracts = []
    # num_papers = 2000
    for idx in tqdm(range(num_papers)):
        try:
            # Using your class instance method to read the clean text
            abstract_text = reader.read_abstract(idx)

            # Handle empty or invalid strings safely
            if not abstract_text or not isinstance(abstract_text, str) or abstract_text.strip() == "":
                abstract_text = ""
        except (FileNotFoundError, ValueError) as e:
            # Handle missing HTML files or missing abstract tags gracefully without breaking the batch
            print(f"Warning at index {idx}: {e}")
            abstract_text = ""

        all_abstracts.append(abstract_text)

    # 5. Generate semantic embeddings in optimized batches using the local model
    print(f"Generating semantic vectors for {len(all_abstracts)} papers...")
    # batch_size=32 or 64 balances memory and parallel execution efficiency on the local CPU/GPU
    all_vectors = model.encode(
        all_abstracts,
        batch_size=32,
        show_progress_bar=True,
        convert_to_numpy=True
    )

    # 6. Save the generated vector matrix to a local binary file
    output_filename = "cvpr2026_semantic_vectors.npy"
    np.save(output_filename, all_vectors)
    print(f"Success! Semantic vectors saved to {output_filename}")
    print(f"Matrix shape: {all_vectors.shape} (Papers, Embedding Dimensions)")


if __name__ == "__main__":
    main()
