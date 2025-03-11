import os
import json
import hashlib
import requests
from typing import Dict, Any, List
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from diskcache import Cache
import tempfile

# Initialize FastAPI
app = FastAPI(title="Spam Detector API")

# Initialize cache in a temporary directory to avoid persistence
cache = Cache(directory=tempfile.mkdtemp())
print(f"Cache initialized in temporary directory: {cache.directory}")

# Ollama configuration
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
MODEL_NAME = os.environ.get("MODEL_NAME", "llama3")

# Check if Ollama is available
try:
    response = requests.get(f"{OLLAMA_HOST}/api/tags")
    if response.status_code == 200:
        models = response.json().get("models", [])
        model_names = [model.get("name") for model in models]
        if MODEL_NAME in model_names:
            print(f"Found {MODEL_NAME} in available models: {model_names}")
        else:
            print(f"Warning: {MODEL_NAME} not found in available models: {model_names}")
            print(f"You may need to run: ollama pull {MODEL_NAME}")
    else:
        print(f"Warning: Could not connect to Ollama at {OLLAMA_HOST}")
except Exception as e:
    print(f"Error connecting to Ollama: {str(e)}")
    print(f"Make sure Ollama is running and accessible at {OLLAMA_HOST}")

print(f"Using Ollama with model {MODEL_NAME} at {OLLAMA_HOST}")

# Prompt template
PROMPT_TEMPLATE = """
Determine if the following text contains signs of spam. Messages are considered spam if they:
- Imitate website names but are written with spaces or dots, for example: 'U SBE T. RU'
- Contain advertising phrases like 'best predictions', 'earn on bets', 'top predictions'
- Use letter combinations similar to domain names

Respond only with a single valid JSON object using this exact schema, and do not include any additional text, explanations, or comments outside the JSON:
{
'is_spam': true/false,
'reason': 'Brief explanation of why the text is classified as spam (or not spam)'
}

Text to analyze: '{text}'
"""

# Request model
class SpamCheckRequest(BaseModel):
    text: str

# Response model
class SpamCheckResponse(BaseModel):
    is_spam: bool
    reason: str
    cached: bool = False

def get_cache_key(text: str) -> str:
    """Generate a cache key for the input text."""
    return hashlib.md5(text.encode('utf-8')).hexdigest()

def extract_json_response(response_text: str) -> Dict[str, Any]:
    """Extract JSON response from model output."""
    json_start = response_text.find('{')
    json_end = response_text.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        json_text = response_text[json_start:json_end]
        try:
            response_json = json.loads(json_text)
            if "is_spam" in response_json and "reason" in response_json:
                return response_json
        except json.JSONDecodeError:
            pass
    
    # Fallback heuristic
    is_spam = "true" in response_text.lower() and "is_spam" in response_text.lower()
    return {
        "is_spam": is_spam,
        "reason": "Failed to get structured response from model, using heuristic instead."
    }

@app.post("/check_spam", response_model=SpamCheckResponse)
async def check_spam(request: SpamCheckRequest) -> Dict[str, Any]:
    # Generate cache key
    cache_key = get_cache_key(request.text)
    
    # Check if response is in cache
    cached_response = cache.get(cache_key)
    if cached_response is not None:
        print(f"Cache hit for request: {request.text[:50]}...")
        return {**cached_response, "cached": True}
    
    print(f"Cache miss for request: {request.text[:50]}...")
    
    # Format the prompt
    prompt = PROMPT_TEMPLATE.replace("{text}", request.text)
    
    try:
        # Generate response using Ollama API
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "stream": False
        }
        
        response = requests.post(f"{OLLAMA_HOST}/api/chat", json=payload)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Extract response from Ollama
        response_json = response.json()
        response_text = response_json.get("message", {}).get("content", "")
        print(f"LLM Response: {response_text}")
        
        # Extract JSON response
        result = extract_json_response(response_text)
        
        # Store in cache
        cache.set(cache_key, result)
        
        # Return with cached=False flag
        return {**result, "cached": False}
            
    except Exception as e:
        print(f"Error calling Ollama API: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    # Check Ollama status
    ollama_status = "unknown"
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags")
        if response.status_code == 200:
            ollama_status = "ok"
    except Exception:
        ollama_status = "error"
    
    return {
        "status": "ok", 
        "model": MODEL_NAME,
        "ollama_host": OLLAMA_HOST,
        "ollama_status": ollama_status,
        "cache_info": {
            "size": len(cache),
            "directory": cache.directory,
            "in_memory": True
        }
    }

@app.get("/cache/stats")
async def cache_stats():
    """Get cache statistics."""
    return {
        "size": len(cache),
        "hits": cache.stats(enable=True)['hits'],
        "misses": cache.stats(enable=True)['misses'],
        "directory": cache.directory
    }

@app.delete("/cache/clear")
async def clear_cache():
    """Clear the cache."""
    cache.clear()
    return {"status": "Cache cleared", "size": len(cache)}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)