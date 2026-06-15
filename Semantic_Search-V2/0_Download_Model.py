import os
from sentence_transformers import SentenceTransformer


def main():
    # Upgrading to BAAI/bge-large-en-v1.5 for significantly better semantic retrieval
    model_name = 'BAAI/bge-large-en-v1.5'
    local_dir = './my_local_model'

    print(f"Downloading model '{model_name}' from Hugging Face...")
    model = SentenceTransformer(model_name)

    print(f"Saving model weights locally to '{local_dir}'...")
    model.save(local_dir)
    print("Download and save complete. Ready to transfer to air-gapped system.")


if __name__ == "__main__":
    main()