"""
Bot Service - HTTP API wrapper for Telegram bot functionality.
Provides REST endpoints for other services to send messages via the bot.
"""
import os
import asyncio
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import logging

from bot_worker import bot_worker


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models for API requests
class SendMessageRequest(BaseModel):
    """Request model for sending messages."""
    to: int  # chat_id or user_id
    type: str = "text"  # text, photo, document, etc.
    payload: Dict[str, Any]  # message content and options


class BulkSendRequest(BaseModel):
    """Request model for sending bulk messages."""
    messages: List[SendMessageRequest]


class BotStatusResponse(BaseModel):
    """Response model for bot status."""
    status: str
    mode: str
    webhook_configured: bool
    commands_count: int


# FastAPI application
app = FastAPI(
    title="RSS Bot Telegram Service",
    description="HTTP API wrapper for Telegram bot functionality",
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


@app.on_event("startup")
async def startup():
    """Initialize bot service on startup."""
    print("Bot service starting...")
    
    # Check if we should run in webhook mode
    webhook_mode = os.getenv("TELEGRAM_WEBHOOK_MODE", "false").lower() == "true"
    
    if webhook_mode and bot_worker.webhook_url:
        # Setup webhook mode (production)
        try:
            await bot_worker.start_webhook(app._state._app if hasattr(app, '_state') else app)
            print("Bot service started in webhook mode")
        except Exception as e:
            print(f"Failed to setup webhook mode: {e}")
            print("Falling back to polling mode")
            webhook_mode = False
    
    if not webhook_mode:
        # Start polling in background for development
        async def start_polling():
            try:
                await bot_worker.start_polling()
            except Exception as e:
                logging.error(f"Polling error: {e}")
        
        # Start polling task in background
        asyncio.create_task(start_polling())
        print("Bot service started in polling mode")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    try:
        # Check if bot is responsive
        bot_info = await bot_worker.bot.get_me()
        return {
            "status": "healthy",
            "service": "bot_svc",
            "bot_username": bot_info.username,
            "bot_id": bot_info.id
        }
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    try:
        # More thorough check
        bot_info = await bot_worker.bot.get_me()
        webhook_info = await bot_worker.bot.get_webhook_info()
        
        return {
            "status": "ready",
            "service": "bot_svc",
            "bot_info": {
                "username": bot_info.username,
                "id": bot_info.id,
                "first_name": bot_info.first_name
            },
            "webhook": {
                "url": webhook_info.url or "Not set (polling mode)",
                "has_custom_certificate": webhook_info.has_custom_certificate,
                "pending_update_count": webhook_info.pending_update_count
            }
        }
    except Exception as e:
        return {"status": "not_ready", "error": str(e)}


@app.post("/send")
async def send_message(
    request: SendMessageRequest,
    token: str = Depends(verify_service_token)
):
    """
    Send a message via the Telegram bot.
    This is the main endpoint other services use to send messages.
    """
    try:
        if request.type == "text":
            # Send simple text message
            result = await bot_worker.send_message(
                chat_id=request.to,
                text=request.payload.get("text", ""),
                parse_mode=request.payload.get("parse_mode", "HTML")
            )
        else:
            # Send formatted message (photos, documents, etc.)
            result = await bot_worker.send_formatted_message(
                chat_id=request.to,
                content={
                    "type": request.type,
                    **request.payload
                }
            )
        
        if result["success"]:
            return {
                "success": True,
                "message_id": result.get("message_id"),
                "chat_id": result.get("chat_id")
            }
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send message: {str(e)}")


@app.post("/send/bulk")
async def send_bulk_messages(
    request: BulkSendRequest,
    background_tasks: BackgroundTasks,
    token: str = Depends(verify_service_token)
):
    """
    Send multiple messages in bulk.
    Messages are sent in background to avoid timeout issues.
    """
    async def process_bulk_messages():
        """Process bulk messages in background."""
        results = []
        for message_request in request.messages:
            try:
                if message_request.type == "text":
                    result = await bot_worker.send_message(
                        chat_id=message_request.to,
                        text=message_request.payload.get("text", ""),
                        parse_mode=message_request.payload.get("parse_mode", "HTML")
                    )
                else:
                    result = await bot_worker.send_formatted_message(
                        chat_id=message_request.to,
                        content={
                            "type": message_request.type,
                            **message_request.payload
                        }
                    )
                results.append(result)
                
                # Small delay to avoid rate limiting
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logging.error(f"Bulk message error: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                    "chat_id": message_request.to
                })
        
        # TODO: Store results in database or send to callback URL
        logging.info(f"Bulk message processing complete: {len(results)} messages")
    
    # Queue background task
    background_tasks.add_task(process_bulk_messages)
    
    return {
        "success": True,
        "message": f"Queued {len(request.messages)} messages for sending",
        "count": len(request.messages)
    }


@app.get("/status", response_model=BotStatusResponse)
async def get_bot_status(token: str = Depends(verify_service_token)):
    """Get current bot status and configuration."""
    try:
        bot_info = await bot_worker.bot.get_me()
        webhook_info = await bot_worker.bot.get_webhook_info()
        commands = await bot_worker.bot.get_my_commands()
        
        return BotStatusResponse(
            status="active",
            mode="webhook" if webhook_info.url else "polling",
            webhook_configured=bool(webhook_info.url),
            commands_count=len(commands)
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot status: {str(e)}")


@app.post("/webhook/telegram")
async def telegram_webhook(request: dict):
    """
    Webhook endpoint for Telegram updates (production mode).
    This endpoint is automatically configured when webhook mode is enabled.
    """
    # Note: In webhook mode, the aiogram SimpleRequestHandler automatically
    # handles this endpoint. This is here for documentation purposes.
    return {"status": "handled_by_aiogram"}


@app.get("/bot/info")
async def get_bot_info(token: str = Depends(verify_service_token)):
    """Get basic bot information."""
    try:
        bot_info = await bot_worker.bot.get_me()
        return {
            "id": bot_info.id,
            "username": bot_info.username,
            "first_name": bot_info.first_name,
            "can_join_groups": bot_info.can_join_groups,
            "can_read_all_group_messages": bot_info.can_read_all_group_messages,
            "supports_inline_queries": bot_info.supports_inline_queries
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get bot info: {str(e)}")


if __name__ == "__main__":
    port = int(os.getenv("BOT_SERVICE_PORT", 8002))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )