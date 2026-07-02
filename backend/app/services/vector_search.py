import os
import math
import hashlib
from typing import List, Dict, Tuple
from google import genai

# Global cache of calculated embeddings representation (ID -> float list vector)
_embeddings_cache: Dict[int, List[float]] = {}

def get_hash_embedding(text: str, dimension: int = 256) -> List[float]:
    """Generates a deterministic, normalized n-gram hashing vector for text lookups."""
    text_clean = text.lower().strip()
    # Build character level n-grams
    grams = (
        [text_clean[i:i+2] for i in range(len(text_clean)-1)] + 
        [text_clean[i:i+3] for i in range(len(text_clean)-2)]
    )
    
    vec = [0.0] * dimension
    if not grams:
        return vec
        
    for gram in grams:
        h = int(hashlib.md5(gram.encode("utf-8")).hexdigest(), 16)
        vec[h % dimension] += 1.0
        
    # Unit normalization
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec

def get_embedding(text: str) -> List[float]:
    """Generate dense embedding vector using Gemini or deterministic n-gram fallback."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            # Use Google GenAI Client
            client = genai.Client(api_key=api_key)
            response = client.models.embed_content(
                model="text-embedding-004",
                contents=text
            )
            if response.embeddings and len(response.embeddings) > 0:
                return response.embeddings[0].values
        except Exception:
            pass # Fallback upon network / context auth failures
            
    return get_hash_embedding(text)

def cosine_similarity(a: List[float], b: List[float]) -> float:
    """Calculate the cosine similarity between two float vectors."""
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)

def semantic_search_topics(query: str, db_topics: List, top_k: int = 10) -> List[Tuple[object, float]]:
    """Calculates vector alignments representing semantic topic recommendations."""
    query_vector = get_embedding(query)
    results = []
    
    for t in db_topics:
        # Cache lookup
        if t.id not in _embeddings_cache:
            _embeddings_cache[t.id] = get_embedding(t.content)
            
        topic_vector = _embeddings_cache[t.id]
        sim = cosine_similarity(query_vector, topic_vector)
        results.append((t, sim))
        
    # Sort by descending cosine alignment similarity
    results.sort(key=lambda x: x[1], reverse=True)
    return results[:top_k]
