from sentence_transformers import SentenceTransformer

# Download from Hugging Face
model = SentenceTransformer('all-MiniLM-L6-v2')
model.save('./my_local_model')
