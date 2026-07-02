import re
from typing import List, Tuple

def calculate_token_overlap(query: str, text: str) -> float:
    """Calculates sparse matching overlap using normalized Jaccard-like query intersection."""
    # Simple regex token extraction
    query_tokens = set(re.findall(r"\w+", query.lower()))
    text_tokens = set(re.findall(r"\w+", text.lower()))
    
    if not query_tokens:
        return 0.0
        
    intersection = query_tokens.intersection(text_tokens)
    # Return proportion of query tokens found in candidate topic content text
    return len(intersection) / len(query_tokens)

def hybrid_rerank(query: str, candidates: List[Tuple[object, float]], top_k: int = 5) -> List[object]:
    """Combines dense vector lookups and sparse term overlap with relevance weights."""
    reranked = []
    
    for topic, dense_score in candidates:
        # Calculate sparse score
        sparse_score = calculate_token_overlap(query, topic.content)
        
        # Combined score calculation (70% semantic embedding alignment, 30% matching density overlap)
        relevance = (0.7 * dense_score) + (0.3 * sparse_score)
        reranked.append((topic, relevance))
        
    # Sort descending by relevance score
    reranked.sort(key=lambda x: x[1], reverse=True)
    
    # Return only the Topic models, capped by top_k
    return [t[0] for t in reranked[:top_k]]
