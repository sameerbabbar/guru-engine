from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import stripe
import json
import resend
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI()

# Allow CORS for the Squarespace frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys Configuration
stripe.api_key = os.getenv("STRIPE_SECRET_KEY_TEST")
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
resend.api_key = os.getenv("RESEND_API_KEY")

# Models
class AuditFormSubmit(BaseModel):
    name: str
    email: str
    company_stage: str
    annual_revenue: str
    primary_bottleneck: str
    co_founder_dynamics: str

@app.post("/api/audit/submit")
async def process_audit_form(data: AuditFormSubmit):
    prompt = f"""
    You are an elite AI concierge for Sameer Babbar's exclusive advisory firm.
    
    Lead Profile:
    Name: {data.name}
    Stage: {data.company_stage}
    Revenue: {data.annual_revenue}
    Dynamics: {data.co_founder_dynamics}
    Bottleneck: {data.primary_bottleneck}
    
    First, score them 1-10 on their viability for a high-ticket retainer ($5k+/month).
    
    If score is >= 5, generate:
    1. 'diagnosis': A 2-sentence, highly consistent, intimidating message. Inform them you have queried Sameer's proprietary database regarding their specific bottleneck and that a private blueprint for this exact failure mode is on file.
    2. 'full_bullets': An array of exactly 5 simple, highly-actionable bullet points detailing what they get in the 1-hour $500 Full Diagnostic.
    3. 'triage_bullets': An array of exactly 2 simple bullet points for the 15-minute $95 Triage. One point MUST explicitly mention that this is a discovery session to ensure mutual fit for an ongoing advisory commitment.
    4. 'internal_briefing': A private briefing for Sameer containing 3 strategic answers/frameworks to use on the call.
    
    Respond STRICTLY with a valid JSON object matching this schema exactly.
    {{
      "score": 8,
      "diagnosis": "Your FOMO-inducing message to the prospect...",
      "full_bullets": ["Point 1", "Point 2", "Point 3", "Point 4", "Point 5"],
      "triage_bullets": ["Point 1", "Point 2"],
      "internal_briefing": "Private analysis for Sameer..."
    }}
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash", generation_config={"response_mime_type": "application/json"})
        response = model.generate_content(prompt)
        
        raw_text = response.text.strip()
        evaluation = json.loads(raw_text)
        score = int(evaluation.get("score", 0))
        
        if score >= 5:
            # Send Email to Sameer
            try:
                # Using resend.dev for testing. Must verify domain on Resend for production.
                resend.Emails.send({
                    "from": "onboarding@resend.dev",
                    "to": "sbabbar@sameerbabbar.com",
                    "subject": f"🚀 HIGH-TICKET LEAD: {data.name}",
                    "html": f"<h2>Lead Profile</h2><p><strong>Name:</strong> {data.name}<br><strong>Email:</strong> {data.email}<br><strong>Revenue:</strong> {data.annual_revenue}</p><h2>Internal Briefing</h2><p>{evaluation.get('internal_briefing')}</p>"
                })
                print("Email dispatched to Sameer successfully.")
            except Exception as email_err:
                print(f"Resend Error (Sameer): {email_err}")

            # Generate Premium Checkout
            checkout_premium = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': 'Full Strategic Alignment Diagnostic'},
                        'unit_amount': 50000,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                customer_email=data.email,
                success_url='https://sameerbabbar.com/success',
            )
            
            # Generate Triage Checkout
            checkout_triage = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {'name': '15-Min Alignment Triage'},
                        'unit_amount': 9500,
                    },
                    'quantity': 1,
                }],
                mode='payment',
                customer_email=data.email,
                success_url='https://sameerbabbar.com/success',
            )
            
            return {
                "status": "qualified", 
                "diagnosis": evaluation.get("diagnosis"),
                "full_bullets": evaluation.get("full_bullets", []),
                "triage_bullets": evaluation.get("triage_bullets", []),
                "url_premium": checkout_premium.url,
                "url_triage": checkout_triage.url
            }
        else:
            return {"status": "unqualified", "redirect_url": "https://sameerbabbar.substack.com/"}
            
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail="Error processing the audit.")

# Vercel Serverless Function Handler
app = app
