"""
AI Service - LLM adapter and AI functionality.
Provides AI-powered content analysis, summarization, and enhancement.
"""
import os
import uvicorn
from datetime import datetime
from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import httpx
import json


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class AIRequest(BaseModel):
    """AI processing request."""
    prompt: str
    content: str
    model: Optional[str] = None
    parameters: Dict[str, Any] = {}
    user_id: Optional[int] = None


class AIResponse(BaseModel):
    """AI processing response."""
    result: str
    model_used: str
    tokens_used: int
    processing_time: float
    metadata: Dict[str, Any]


class SummarizeRequest(BaseModel):
    """Content summarization request."""
    content: str
    max_length: int = 200
    style: str = "neutral"  # neutral, casual, formal, technical
    language: str = "en"


class ExtractRequest(BaseModel):
    """Content extraction request."""
    content: str
    extract_type: str  # keywords, entities, sentiment, topics
    parameters: Dict[str, Any] = {}


class UsageStats(BaseModel):
    """AI usage statistics."""
    user_id: int
    total_requests: int
    total_tokens: int
    requests_today: int
    tokens_today: int
    quota_remaining: int


# FastAPI application
app = FastAPI(
    title="RSS Bot AI Service",
    description="LLM adapter and AI functionality service",
    version="0.1.0",
)

# Add CORS middleware for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory usage tracking (use database in production)
usage_storage: Dict[int, UsageStats] = {}

# AI service configuration
AI_CONFIG = {
    "default_model": os.getenv("AI_MODEL", "gpt-3.5-turbo"),
    "openai_api_key": os.getenv("OPENAI_API_KEY"),
    "max_tokens_per_request": 2000,
    "daily_quota": {
        "free": 1000,
        "premium": 10000,
        "enterprise": 100000
    }
}


@app.on_event("startup")
async def startup():
    """Initialize AI service."""
    print("AI service started successfully")
    
    if not AI_CONFIG["openai_api_key"]:
        print("Warning: OPENAI_API_KEY not configured - AI features will use mock responses")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "ai_svc",
        "api_key_configured": bool(AI_CONFIG["openai_api_key"]),
        "default_model": AI_CONFIG["default_model"]
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "ai_svc",
        "features": ["summarization", "keyword_extraction", "sentiment_analysis", "content_enhancement"]
    }


async def call_openai_api(prompt: str, model: str = None, max_tokens: int = 1000) -> Dict[str, Any]:
    """Call OpenAI API (or simulate for development)."""
    if not AI_CONFIG["openai_api_key"]:
        # Mock response for development
        return {
            "result": f"[MOCK AI RESPONSE] Processed content: {prompt[:100]}...",
            "model": model or AI_CONFIG["default_model"],
            "tokens_used": len(prompt.split()) + 20,
            "mock": True
        }
    
    try:
        # TODO: Implement actual OpenAI API call
        # This is a placeholder for the real implementation
        
        headers = {
            "Authorization": f"Bearer {AI_CONFIG['openai_api_key']}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model or AI_CONFIG["default_model"],
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        # For now, return mock response
        return {
            "result": f"AI analysis of content: {prompt[:100]}... [Generated with {model or AI_CONFIG['default_model']}]",
            "model": model or AI_CONFIG["default_model"],
            "tokens_used": len(prompt.split()) + 50,
            "mock": False
        }
        
    except Exception as e:
        raise ValueError(f"AI API call failed: {str(e)}")


def get_user_usage(user_id: int) -> UsageStats:
    """Get or create user usage statistics."""
    if user_id not in usage_storage:
        usage_storage[user_id] = UsageStats(
            user_id=user_id,
            total_requests=0,
            total_tokens=0,
            requests_today=0,
            tokens_today=0,
            quota_remaining=AI_CONFIG["daily_quota"]["free"]
        )
    return usage_storage[user_id]


def update_usage(user_id: int, tokens_used: int):
    """Update user usage statistics."""
    stats = get_user_usage(user_id)
    stats.total_requests += 1
    stats.total_tokens += tokens_used
    stats.requests_today += 1
    stats.tokens_today += tokens_used
    stats.quota_remaining = max(0, stats.quota_remaining - tokens_used)


@app.post("/call", response_model=AIResponse)
async def call_ai(
    request: AIRequest,
    token: str = Depends(verify_service_token)
):
    """Make a general AI call with custom prompt."""
    start_time = datetime.now()
    
    try:
        # Check usage quota if user_id provided
        if request.user_id:
            usage = get_user_usage(request.user_id)
            if usage.quota_remaining <= 0:
                raise HTTPException(status_code=429, detail="AI quota exceeded")
        
        # Call AI API
        result = await call_openai_api(
            prompt=request.prompt + "\n\nContent: " + request.content,
            model=request.model,
            max_tokens=request.parameters.get("max_tokens", 1000)
        )
        
        # Update usage tracking
        if request.user_id:
            update_usage(request.user_id, result["tokens_used"])
        
        processing_time = (datetime.now() - start_time).total_seconds()
        
        return AIResponse(
            result=result["result"],
            model_used=result["model"],
            tokens_used=result["tokens_used"],
            processing_time=processing_time,
            metadata={
                "mock_response": result.get("mock", False),
                "user_id": request.user_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI processing failed: {str(e)}")


@app.post("/summarize", response_model=AIResponse)
async def summarize_content(
    request: SummarizeRequest,
    user_id: Optional[int] = None,
    token: str = Depends(verify_service_token)
):
    """Summarize content with specific parameters."""
    prompt = f"""
Summarize the following content in {request.max_length} characters or less.
Use a {request.style} tone and {request.language} language.
Focus on the key points and maintain accuracy.

Content to summarize:
"""
    
    ai_request = AIRequest(
        prompt=prompt,
        content=request.content,
        user_id=user_id,
        parameters={"max_tokens": request.max_length // 4}  # Rough token estimate
    )
    
    return await call_ai(ai_request, token)


@app.post("/extract", response_model=AIResponse)
async def extract_from_content(
    request: ExtractRequest,
    user_id: Optional[int] = None,
    token: str = Depends(verify_service_token)
):
    """Extract specific information from content."""
    prompts = {
        "keywords": "Extract the top 10 most relevant keywords from the following content. Return as a comma-separated list:",
        "entities": "Extract named entities (people, places, organizations) from the following content:",
        "sentiment": "Analyze the sentiment of the following content. Return: positive, negative, or neutral with confidence score:",
        "topics": "Identify the main topics discussed in the following content. Return up to 5 topics:"
    }
    
    if request.extract_type not in prompts:
        raise HTTPException(status_code=400, detail=f"Unsupported extraction type: {request.extract_type}")
    
    ai_request = AIRequest(
        prompt=prompts[request.extract_type],
        content=request.content,
        user_id=user_id,
        parameters=request.parameters
    )
    
    return await call_ai(ai_request, token)


@app.post("/enhance")
async def enhance_content(
    content: str,
    enhancement_type: str,
    parameters: Dict[str, Any] = {},
    user_id: Optional[int] = None,
    token: str = Depends(verify_service_token)
):
    """Enhance content for Telegram formatting."""
    enhancement_prompts = {
        "telegram_format": "Convert the following content to engaging Telegram format with appropriate emojis and formatting. Keep it under 4000 characters:",
        "add_hashtags": "Add relevant hashtags to the following content for better discoverability:",
        "improve_readability": "Improve the readability and engagement of the following content while maintaining accuracy:",
        "translate": f"Translate the following content to {parameters.get('target_language', 'English')}:"
    }
    
    if enhancement_type not in enhancement_prompts:
        raise HTTPException(status_code=400, detail=f"Unsupported enhancement type: {enhancement_type}")
    
    ai_request = AIRequest(
        prompt=enhancement_prompts[enhancement_type],
        content=content,
        user_id=user_id,
        parameters=parameters
    )
    
    return await call_ai(ai_request, token)


@app.get("/usage/{user_id}", response_model=UsageStats)
async def get_usage_stats(
    user_id: int,
    token: str = Depends(verify_service_token)
):
    """Get AI usage statistics for a user."""
    return get_user_usage(user_id)


@app.get("/models")
async def list_available_models(token: str = Depends(verify_service_token)):
    """List available AI models."""
    return {
        "models": [
            {
                "name": "gpt-3.5-turbo",
                "description": "Fast and cost-effective for most tasks",
                "max_tokens": 4000,
                "cost_per_1k_tokens": 0.002
            },
            {
                "name": "gpt-4",
                "description": "Most capable model for complex tasks",
                "max_tokens": 8000,
                "cost_per_1k_tokens": 0.03
            }
        ],
        "default": AI_CONFIG["default_model"]
    }


@app.get("/stats")
async def get_service_stats(token: str = Depends(verify_service_token)):
    """Get AI service statistics."""
    total_requests = sum(stats.total_requests for stats in usage_storage.values())
    total_tokens = sum(stats.total_tokens for stats in usage_storage.values())
    active_users = len(usage_storage)
    
    return {
        "total_requests": total_requests,
        "total_tokens": total_tokens,
        "active_users": active_users,
        "api_configured": bool(AI_CONFIG["openai_api_key"]),
        "default_model": AI_CONFIG["default_model"]
    }


@app.post("/reset-quota/{user_id}")
async def reset_user_quota(
    user_id: int,
    new_quota: int,
    token: str = Depends(verify_service_token)
):
    """Reset user's daily quota (admin function)."""
    if user_id in usage_storage:
        usage_storage[user_id].quota_remaining = new_quota
        usage_storage[user_id].requests_today = 0
        usage_storage[user_id].tokens_today = 0
    
    return {"message": f"Quota reset for user {user_id}", "new_quota": new_quota}


if __name__ == "__main__":
    port = int(os.getenv("AI_SERVICE_PORT", 8005))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )