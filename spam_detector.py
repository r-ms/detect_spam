import os
import json
import hashlib
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from huggingface_hub import login
from diskcache import Cache
import tempfile

# Initialize FastAPI
app = FastAPI(title="Spam Detector API")

# Initialize cache in a temporary directory to avoid persistence
cache = Cache(directory=tempfile.mkdtemp())
print(f"Cache initialized in temporary directory: {cache.directory}")

# Model configuration
MODEL_ID = os.environ.get("MODEL_ID", "meta-llama/Llama-3-8B-Instruct")  # Using Llama 3 Instruct model
DEVICE = os.environ.get("DEVICE", "cpu")  # Running on CPU

# Login to Hugging Face if token is provided
hf_token = os.environ.get("HF_TOKEN")
if hf_token:
    print("Logging in to Hugging Face with provided token...")
    login(token=hf_token)
    print("Successfully logged in to Hugging Face")
else:
    print("Warning: HF_TOKEN not provided. Access to gated models may be restricted.")

# Initialize model when server starts
print(f"Loading model {MODEL_ID} on {DEVICE}...")
tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    device_map=DEVICE,
    low_cpu_mem_usage=True,
    torch_dtype="auto"
)
generator = pipeline(
    "text-generation",
    model=model,
    tokenizer=tokenizer,
    max_new_tokens=200,
    temperature=0.1,
    do_sample=True
)
print("Model loaded successfully!")

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
        # Generate response using transformers pipeline
        generated_text = generator(prompt, max_new_tokens=200, temperature=0.1)[0]['generated_text']
        
        # Extract only the generated part (not the prompt)
        response_text = generated_text[len(prompt):].strip()
        print(f"LLM Response: {response_text}")
        
        # Extract JSON response
        result = extract_json_response(response_text)
        
        # Store in cache
        cache.set(cache_key, result)
        
        # Return with cached=False flag
        return {**result, "cached": False}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.get("/health")
async def health_check():
    return {
        "status": "ok", 
        "model": MODEL_ID,
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