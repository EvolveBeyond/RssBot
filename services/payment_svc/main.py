"""
Payment Service - Payment and invoice gateway.
Handles Telegram Payments and external payment providers.
"""
import os
import uvicorn
import hmac
import hashlib
import json
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import httpx
import asyncio


# Security middleware for inter-service authentication
async def verify_service_token(x_service_token: Optional[str] = Header(None)):
    """Verify service-to-service authentication token."""
    expected_token = os.getenv("SERVICE_TOKEN", "dev_service_token_change_in_production")
    if x_service_token != expected_token:
        raise HTTPException(status_code=401, detail="Invalid service token")
    return x_service_token


# Pydantic models
class InvoiceRequest(BaseModel):
    """Invoice creation request."""
    user_id: int
    plan_id: str
    amount: float  # Amount in USD cents
    currency: str = "USD"
    platform: str = "telegram"  # telegram, stripe, etc.
    description: str
    metadata: Dict[str, Any] = {}


class InvoiceResponse(BaseModel):
    """Invoice creation response."""
    invoice_id: str
    status: str
    amount: float
    currency: str
    platform: str
    payment_url: Optional[str] = None
    telegram_invoice_payload: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None


class PaymentUpdate(BaseModel):
    """Payment status update."""
    invoice_id: str
    status: str
    external_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class WebhookEvent(BaseModel):
    """Webhook event data."""
    event_type: str
    data: Dict[str, Any]
    signature: Optional[str] = None


# FastAPI application
app = FastAPI(
    title="RSS Bot Payment Service",
    description="Payment and invoice gateway for the RSS Bot platform",
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

# In-memory payment storage (use database in production)
payments_storage: Dict[str, InvoiceResponse] = {}

# Payment plans configuration
PAYMENT_PLANS = {
    "premium_monthly": {
        "name": "Premium Monthly",
        "amount": 999,  # $9.99 in cents
        "currency": "USD",
        "duration": "1 month",
        "features": ["Unlimited channels", "Custom formatting", "Priority support"]
    },
    "premium_yearly": {
        "name": "Premium Yearly", 
        "amount": 9999,  # $99.99 in cents
        "currency": "USD",
        "duration": "1 year",
        "features": ["Unlimited channels", "Custom formatting", "Priority support", "2 months free"]
    },
    "enterprise": {
        "name": "Enterprise",
        "amount": 4999,  # $49.99 in cents
        "currency": "USD",
        "duration": "1 month",
        "features": ["Everything in Premium", "API access", "Custom integrations", "Dedicated support"]
    }
}


@app.on_event("startup")
async def startup():
    """Initialize payment service."""
    print("Payment service started successfully")


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "payment_svc",
        "supported_platforms": ["telegram", "stripe", "simulator"]
    }


@app.get("/ready")
async def readiness_check():
    """Readiness check endpoint."""
    return {
        "status": "ready",
        "service": "payment_svc",
        "available_plans": list(PAYMENT_PLANS.keys())
    }


@app.get("/plans")
async def get_payment_plans(token: str = Depends(verify_service_token)):
    """Get available payment plans."""
    return {
        "plans": PAYMENT_PLANS,
        "count": len(PAYMENT_PLANS)
    }


def generate_invoice_id() -> str:
    """Generate unique invoice ID."""
    timestamp = str(int(datetime.now().timestamp()))
    return f"inv_{timestamp}_{hash(timestamp) % 10000}"


async def create_telegram_invoice(request: InvoiceRequest) -> Dict[str, Any]:
    """Create Telegram payment invoice."""
    # TODO: Implement actual Telegram Payments API integration
    # This is a simulation for development
    
    plan = PAYMENT_PLANS.get(request.plan_id)
    if not plan:
        raise ValueError(f"Unknown plan: {request.plan_id}")
    
    telegram_payload = {
        "title": plan["name"],
        "description": request.description,
        "payload": f"plan_{request.plan_id}_{request.user_id}",
        "provider_token": os.getenv("TELEGRAM_PAYMENTS_PROVIDER_TOKEN", "TEST_TOKEN"),
        "currency": request.currency,
        "prices": [{"label": plan["name"], "amount": int(request.amount)}],
        "need_email": True,
        "send_email_to_provider": True,
    }
    
    return {
        "telegram_invoice_payload": telegram_payload,
        "payment_url": None  # Telegram handles this via bot
    }


async def create_stripe_invoice(request: InvoiceRequest) -> Dict[str, Any]:
    """Create Stripe payment session."""
    # TODO: Implement actual Stripe integration
    # This is a simulation for development
    
    stripe_session_id = f"cs_test_{generate_invoice_id()}"
    payment_url = f"https://checkout.stripe.com/pay/{stripe_session_id}"
    
    return {
        "telegram_invoice_payload": None,
        "payment_url": payment_url,
        "stripe_session_id": stripe_session_id
    }


async def create_simulator_invoice(request: InvoiceRequest) -> Dict[str, Any]:
    """Create simulated payment for development."""
    return {
        "telegram_invoice_payload": None,
        "payment_url": f"http://localhost:8003/simulator/pay/{generate_invoice_id()}",
        "simulation": True
    }


@app.post("/invoice", response_model=InvoiceResponse)
async def create_invoice(
    request: InvoiceRequest,
    token: str = Depends(verify_service_token)
):
    """Create a payment invoice."""
    try:
        invoice_id = generate_invoice_id()
        
        # Validate plan exists
        if request.plan_id not in PAYMENT_PLANS:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {request.plan_id}")
        
        # Create platform-specific invoice
        platform_data = {}
        
        if request.platform == "telegram":
            platform_data = await create_telegram_invoice(request)
        elif request.platform == "stripe":
            platform_data = await create_stripe_invoice(request)
        elif request.platform == "simulator":
            platform_data = await create_simulator_invoice(request)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported platform: {request.platform}")
        
        # Create invoice response
        invoice = InvoiceResponse(
            invoice_id=invoice_id,
            status="pending",
            amount=request.amount,
            currency=request.currency,
            platform=request.platform,
            payment_url=platform_data.get("payment_url"),
            telegram_invoice_payload=platform_data.get("telegram_invoice_payload"),
            expires_at=datetime.now() + timedelta(hours=24)
        )
        
        # Store invoice
        payments_storage[invoice_id] = invoice
        
        return invoice
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create invoice: {str(e)}")


@app.get("/invoice/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(
    invoice_id: str,
    token: str = Depends(verify_service_token)
):
    """Get invoice details."""
    if invoice_id not in payments_storage:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    
    return payments_storage[invoice_id]


@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Handle Telegram payment webhooks."""
    try:
        data = await request.json()
        
        # TODO: Implement proper Telegram webhook signature verification
        # webhook_secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        
        # Process payment update
        if "successful_payment" in data:
            payment_data = data["successful_payment"]
            invoice_payload = payment_data.get("invoice_payload", "")
            
            # Extract invoice info from payload
            if invoice_payload.startswith("plan_"):
                parts = invoice_payload.split("_")
                if len(parts) >= 3:
                    plan_id, user_id = parts[1], parts[2]
                    
                    # TODO: Update payment status in database via db_svc
                    # TODO: Update user subscription level via user_svc
                    
                    await process_successful_payment({
                        "plan_id": plan_id,
                        "user_id": int(user_id),
                        "amount": payment_data.get("total_amount"),
                        "currency": payment_data.get("currency"),
                        "telegram_payment_id": payment_data.get("telegram_payment_charge_id")
                    })
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Telegram webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


@app.post("/webhook/stripe")
async def stripe_webhook(request: Request):
    """Handle Stripe payment webhooks."""
    try:
        data = await request.json()
        signature = request.headers.get("stripe-signature")
        
        # TODO: Implement proper Stripe webhook signature verification
        # stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        
        event_type = data.get("type")
        
        if event_type == "checkout.session.completed":
            session = data.get("data", {}).get("object", {})
            # Process successful payment
            await process_successful_payment({
                "stripe_session_id": session.get("id"),
                "amount": session.get("amount_total"),
                "currency": session.get("currency"),
                "metadata": session.get("metadata", {})
            })
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Stripe webhook error: {e}")
        raise HTTPException(status_code=400, detail="Webhook processing failed")


async def process_successful_payment(payment_data: Dict[str, Any]):
    """Process a successful payment and update user subscription."""
    try:
        # TODO: Call db_svc to record payment
        # TODO: Call user_svc to upgrade subscription
        
        print(f"Processing successful payment: {payment_data}")
        
        # Simulate database update
        await asyncio.sleep(0.1)
        
        # Update local payment status if we have the invoice
        for invoice_id, invoice in payments_storage.items():
            if (invoice.status == "pending" and 
                payment_data.get("amount") == invoice.amount):
                invoice.status = "completed"
                break
        
        print("Payment processed successfully")
        
    except Exception as e:
        print(f"Payment processing error: {e}")


@app.get("/simulator/pay/{invoice_id}")
async def payment_simulator(invoice_id: str):
    """Payment simulator for development."""
    if invoice_id not in payments_storage:
        return {"error": "Invoice not found"}
    
    # Simulate payment completion
    invoice = payments_storage[invoice_id]
    invoice.status = "completed"
    
    # Simulate webhook callback
    await process_successful_payment({
        "invoice_id": invoice_id,
        "amount": invoice.amount,
        "currency": invoice.currency,
        "simulation": True
    })
    
    return {
        "message": "Payment simulation completed",
        "invoice_id": invoice_id,
        "status": "completed"
    }


@app.get("/payments")
async def list_payments(token: str = Depends(verify_service_token)):
    """List all payment records."""
    return {
        "payments": list(payments_storage.values()),
        "count": len(payments_storage)
    }


@app.post("/payments/{invoice_id}/cancel")
async def cancel_payment(
    invoice_id: str,
    token: str = Depends(verify_service_token)
):
    """Cancel a pending payment."""
    if invoice_id not in payments_storage:
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = payments_storage[invoice_id]
    if invoice.status != "pending":
        raise HTTPException(status_code=400, detail="Cannot cancel non-pending payment")
    
    invoice.status = "cancelled"
    return {"message": "Payment cancelled", "invoice_id": invoice_id}


if __name__ == "__main__":
    port = int(os.getenv("PAYMENT_SERVICE_PORT", 8003))
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )