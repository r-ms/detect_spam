import os
import json
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from vllm import LLM, SamplingParams
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
llm = LLM(model=MODEL_ID, tensor_parallel_size=1, device=DEVICE)
print("Model loaded successfully!")

# Parameters for response generation
sampling_params = SamplingParams(
    temperature=0.1,  # Low temperature for more deterministic responses
    max_tokens=200,
    stop_token=["</s>"]  # Stop token for Llama 3
)

# Prompt template
PROMPT_TEMPLATE = """
Determine if the following text contains signs of spam. Messages are considered spam if they: 
- Imitate website names but are written with spaces or dots, for example: "U SBE T. RU" 
- Contain advertising phrases like "best predictions", "earn on bets", "top predictions" 
- Use letter combinations similar to domain names 

The answer should be in JSON format: 
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
        # Send request to the model
        outputs = llm.generate(prompt, sampling_params)
        generated_text = outputs[0].outputs[0].text.strip()
        
        # Try to parse JSON from the response
        try:
            response_json = json.loads(generated_text)
            # Check if required fields are present
            if "is_spam" not in response_json or "reason" not in response_json:
                raise ValueError("Incomplete response from model")
                
            return {
                "is_spam": response_json["is_spam"],
                "reason": response_json["reason"]
            }
        except json.JSONDecodeError:
            # If JSON parsing fails, try to extract the answer from the text
            print(f"Failed to parse JSON from response: {generated_text}")
            
            # Simplified fallback: check for key words
            is_spam = "true" in generated_text.lower() and "is_spam" in generated_text.lower()
            
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