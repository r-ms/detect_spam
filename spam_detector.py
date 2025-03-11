import os
import json
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
from huggingface_hub import login

# Initialize FastAPI
app = FastAPI(title="Spam Detector API")

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
- Imitate website names but are written with spaces or dots, for example: "U SBE T. RU" 
- Contain advertising phrases like "best predictions", "earn on bets", "top predictions" 
- Use letter combinations similar to domain names 

The answer must be in JSON format: 
{{
"is_spam": true/false,
"reason": "Brief explanation of why the text is classified as spam (or not spam)"
}}

Text to analyze: 
"{text}"
"""

# Request model
class SpamCheckRequest(BaseModel):
    text: str

# Response model
class SpamCheckResponse(BaseModel):
    is_spam: bool
    reason: str

@app.post("/check_spam", response_model=SpamCheckResponse)
async def check_spam(request: SpamCheckRequest) -> Dict[str, Any]:
    # Format the prompt
    prompt = PROMPT_TEMPLATE.format(text=request.text)
    
    try:
        # Generate response using transformers pipeline
        generated_text = generator(prompt, max_new_tokens=200, temperature=0.1)[0]['generated_text']
        
        # Extract only the generated part (not the prompt)
        response_text = generated_text[len(prompt):].strip()
        print(f"LLM Response: {response_text}")
        
        # Try to parse JSON from the response
        try:
            # Find JSON object in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_text = response_text[json_start:json_end]
                response_json = json.loads(json_text)
                
                # Check if required fields are present
                if "is_spam" not in response_json or "reason" not in response_json:
                    raise ValueError("Incomplete response from model")
                    
                return {
                    "is_spam": response_json["is_spam"],
                    "reason": response_json["reason"]
                }
            else:
                raise ValueError("No JSON found in response")
                
        except (json.JSONDecodeError, ValueError) as e:
            # If JSON parsing fails, try to extract the answer from the text
            print(f"Failed to parse JSON from response: {response_text}")
            print(f"Error: {str(e)}")
            
            # Simplified fallback: check for key words
            is_spam = "true" in response_text.lower() and "is_spam" in response_text.lower()
            
            return {
                "is_spam": is_spam,
                "reason": "Failed to get structured response from model, using heuristic instead."
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    return {"status": "ok", "model": MODEL_ID}

# Run the server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)