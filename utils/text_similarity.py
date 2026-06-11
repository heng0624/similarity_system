from sentence_transformers import SentenceTransformer, util

# Load model once(Transformer-based Sentence Embedding Model)
model = SentenceTransformer("all-MiniLM-L6-v2")

# Return only embedding (for cache)
def get_text_embedding(text):
    return model.encode(text)

# Full similarity computation
def compute_text_similarity(text1, text2):
    vec1 = get_text_embedding(text1)
    vec2 = get_text_embedding(text2)
    return float(util.cos_sim(vec1, vec2))
