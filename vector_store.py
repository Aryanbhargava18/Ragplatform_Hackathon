import os
import json
import time
import math
import numpy as np
from datetime import datetime
import openai
from openai import OpenAI
import threading
import redis
from redis_cache import get_redis_client, get_cached_result, cache_result
from utils import format_datetime

# Initialize OpenAI client
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

# Global in-memory store for documents and embeddings
# In a production environment, this would be a persistent vector database
documents = {}
document_embeddings = {}
keyword_index = {}
locks = {
    "documents": threading.Lock(),
    "embeddings": threading.Lock(),
    "keywords": threading.Lock()
}

def generate_embedding(text):
    """
    Generate embedding vector for text using OpenAI
    """
    try:
        # Check cache first
        cache_key = f"embedding:{hash(text)}"
        cached_embedding = get_cached_result(cache_key)
        if cached_embedding:
            return json.loads(cached_embedding)
        
        # Generate new embedding
        response = client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        embedding = response.data[0].embedding
        
        # Cache the result
        cache_result(cache_key, json.dumps(embedding))
        
        return embedding
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        # Return a zero vector as fallback
        return [0.0] * 1536  # Ada embeddings are 1536 dimensions

def update_vector_index(document_id, content):
    """
    Update the vector index with new document embeddings
    For demo purposes, this just returns the content
    In production, this would use a vector database
    """
    try:
        # In a production environment, we would:
        # 1. Generate embeddings using OpenAI
        # 2. Store them in a vector database
        # 3. Update the index
        
        # For demo, just return success
        return True
    except Exception as e:
        print(f"Error updating vector index: {str(e)}")
        return False

def search_similar_documents(query, top_k=5):
    """
    Search for similar documents using vector similarity
    For demo purposes, this returns mock results
    """
    try:
        # Mock results
        return [
            {
                "id": f"DOC-{i}",
                "title": f"Similar Document {i}",
                "similarity": 0.9 - (i * 0.1),
                "content": "This is a mock similar document."
            }
            for i in range(top_k)
        ]
    except Exception as e:
        print(f"Error searching similar documents: {str(e)}")
        return []

def vector_similarity(vec1, vec2):
    """
    Calculate cosine similarity between two vectors
    """
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = math.sqrt(sum(a * a for a in vec1))
    magnitude2 = math.sqrt(sum(b * b for b in vec2))
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0
    
    return dot_product / (magnitude1 * magnitude2)

def bm25_score(query_terms, document, k1=1.5, b=0.75, avg_doc_len=None):
    """
    Calculate BM25 score for keyword matching
    """
    if not query_terms or not document:
        return 0
    
    # Extract document content and terms
    doc_content = document["content"].lower()
    doc_terms = set(doc_content.split())
    
    # If no average document length is provided, use this document's length
    if avg_doc_len is None:
        avg_doc_len = len(doc_terms)
    
    # Calculate IDF and term frequency components
    score = 0
    for term in query_terms:
        if term in doc_terms:
            # Term frequency in the document
            tf = doc_content.count(term)
            
            # Document length normalization
            doc_len = len(doc_terms)
            norm_factor = 1 - b + b * (doc_len / avg_doc_len)
            
            # BM25 formula component
            term_score = tf * (k1 + 1) / (tf + k1 * norm_factor)
            
            # We don't have a corpus IDF, so use a simplified approach
            # Assume all query terms are equally important
            score += term_score
    
    return score

def query_hybrid_index(query, jurisdiction=None, top_k=5):
    """
    Query the hybrid index (vector + keyword) with a given query
    """
    # Check cache first
    cache_key = f"query:{query}:{jurisdiction}:{top_k}"
    cached_results = get_cached_result(cache_key)
    if cached_results:
        return json.loads(cached_results)
    
    # Generate embedding for the query
    query_embedding = generate_embedding(query)
    
    # Calculate similarity scores for all documents
    results = []
    
    with locks["documents"]:
        doc_ids = list(documents.keys())
    
    # Extract query terms for keyword matching
    query_terms = set(query.lower().split())
    
    for doc_id in doc_ids:
        with locks["documents"]:
            doc = documents.get(doc_id)
        
        if not doc:
            continue
        
        # Filter by jurisdiction if specified
        if jurisdiction and doc["jurisdiction"] != jurisdiction:
            continue
        
        # Get document embedding
        with locks["embeddings"]:
            doc_embedding = document_embeddings.get(doc_id)
        
        if not doc_embedding:
            continue
        
        # Calculate vector similarity score
        vector_score = vector_similarity(query_embedding, doc_embedding)
        
        # Calculate keyword matching score
        keyword_score = bm25_score(query_terms, doc)
        
        # Combined score - 70% vector similarity, 30% keyword matching
        combined_score = 0.7 * vector_score + 0.3 * keyword_score
        
        # Add to results
        results.append({
            "id": doc_id,
            "title": doc["title"],
            "date": doc["date"],
            "source": doc["source"],
            "jurisdiction": doc["jurisdiction"],
            "score": combined_score,
            "risk_score": doc["risk_score"],
            "excerpt": doc["content"][:200] + "..." if len(doc["content"]) > 200 else doc["content"]
        })
    
    # Sort by score and take top_k
    results = sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]
    
    # Cache results
    cache_result(cache_key, json.dumps(results), ttl=300)  # 5 minutes TTL
    
    return results

def get_latest_documents(jurisdiction=None, min_risk=None, search_query=None, limit=10):
    """
    Get the latest documents with optional filtering
    """
    # Convert min_risk string to float
    risk_level_map = {
        "Low": 0.25,
        "Medium": 0.5,
        "High": 0.75,
        "Critical": 0.9
    }
    
    min_risk_value = risk_level_map.get(min_risk, 0.0) if min_risk else 0.0
    
    # Build results
    results = []
    
    with locks["documents"]:
        doc_ids = list(documents.keys())
    
    for doc_id in doc_ids:
        with locks["documents"]:
            doc = documents.get(doc_id)
        
        if not doc:
            continue
        
        # Filter by jurisdiction if specified
        if jurisdiction and doc["jurisdiction"] != jurisdiction:
            continue
        
        # Filter by risk level
        if doc["risk_score"] < min_risk_value:
            continue
        
        # Filter by search query
        if search_query:
            # Simple text search in title and content
            query_lower = search_query.lower()
            title_match = query_lower in doc["title"].lower()
            content_match = query_lower in doc["content"].lower()
            keyword_match = any(query_lower in keyword.lower() for keyword in doc["keywords"])
            
            if not (title_match or content_match or keyword_match):
                continue
        
        # Add to results
        results.append({
            "id": doc_id,
            "title": doc["title"],
            "content": doc["content"],
            "date": doc["date"],
            "source": doc["source"],
            "jurisdiction": doc["jurisdiction"],
            "risk_score": doc["risk_score"],
            "keywords": doc["keywords"],
            "summary": doc["content"][:150] + "..." if len(doc["content"]) > 150 else doc["content"]
        })
    
    # Sort by timestamp (newest first) and take the limit
    results = sorted(results, key=lambda x: documents[x["id"]]["timestamp"], reverse=True)[:limit]
    
    return results
