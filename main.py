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

@app.get("/")
async def root():
    return {"status": "Sameer Babbar Advisory Engine is Active", "version": "1.0"}

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
            # 1. Generate Stripe Checkout sessions FIRST so we can include links in both emails
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
            
            # Format text parameters for clean HTML rendering
            dynamics = data.co_founder_dynamics
            bottleneck = data.primary_bottleneck.replace('\n', '<br>')
            briefing_html = evaluation.get('internal_briefing', '').replace('\n', '<br>')
            diagnosis_html = evaluation.get('diagnosis', '').replace('\n', '<br>')

            # 2. Send Executive Report Email to Sameer & Bigpond
            try:
                sameer_email_body = f"""
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; padding: 30px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e1e1e1; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                        <!-- Header -->
                        <div style="background-color: #1a1a1a; color: #ffffff; padding: 40px 30px; text-align: center; border-bottom: 4px solid #ffcc00;">
                            <h1 style="margin: 0; font-size: 20px; letter-spacing: 2px; text-transform: uppercase; font-weight: 700;">Sameer Babbar Advisory</h1>
                            <p style="margin: 8px 0 0 0; font-size: 11px; color: #ffcc00; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold;">Internal Lead Intelligence Report</p>
                        </div>
                        
                        <!-- Content Body -->
                        <div style="padding: 35px 30px;">
                            <h2 style="font-size: 15px; margin-top: 0; margin-bottom: 15px; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; text-transform: uppercase; color: #1a1a1a; letter-spacing: 0.5px;">Lead Profile</h2>
                            <table style="width: 100%; border-collapse: collapse; margin-bottom: 35px; font-size: 14px;">
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; font-weight: bold; width: 160px; color: #666; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Full Name:</td>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; font-weight: bold; color: #1a1a1a; font-size: 15px;">{data.name}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; font-weight: bold; color: #666; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Work Email:</td>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #1a1a1a; font-size: 14px;"><a href="mailto:{data.email}" style="color: #1a1a1a; text-decoration: underline;">{data.email}</a></td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #666; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Company Stage:</td>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #1a1a1a; font-weight: 500;">{data.company_stage}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #666; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Annual Revenue:</td>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #1a1a1a; font-weight: 500;">{data.annual_revenue}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #666; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Cofounder Dynamics:</td>
                                    <td style="padding: 12px 0; border-bottom: 1px solid #f0f0f0; color: #1a1a1a;">{dynamics}</td>
                                </tr>
                                <tr>
                                    <td style="padding: 12px 0; color: #666; vertical-align: top; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px;">Primary Bottleneck:</td>
                                    <td style="padding: 12px 0; color: #1a1a1a; line-height: 1.6; font-size: 14px;">{bottleneck}</td>
                                </tr>
                            </table>
                            
                            <h2 style="font-size: 15px; margin-top: 0; margin-bottom: 15px; border-bottom: 2px solid #1a1a1a; padding-bottom: 8px; text-transform: uppercase; color: #1a1a1a; letter-spacing: 0.5px;">AI Closing Intelligence & Strategic Frameworks</h2>
                            <div style="background-color: #fcfcfc; border-left: 4px solid #ffcc00; border-top: 1px solid #eee; border-right: 1px solid #eee; border-bottom: 1px solid #eee; padding: 25px; font-size: 14px; line-height: 1.7; color: #222; margin-top: 15px; font-style: italic;">
                                {briefing_html}
                            </div>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #fafafa; border-top: 1px solid #eee; padding: 25px; text-align: center; font-size: 11px; color: #888; line-height: 1.5;">
                            This report was autonomously compiled by the Sameer Babbar Advisory Concierge Engine.<br>
                            All content is proprietary, confidential, and prepared for internal briefing prior to alignment calls.
                        </div>
                    </div>
                </div>
                """
                resend.Emails.send({
                    "from": "advisory@sameerbabbar.com",
                    "to": "sbabbar@sameerbabbar.com",
                    "subject": f"🚀 HIGH-TICKET LEAD: {data.name} ({data.company_stage})",
                    "html": sameer_email_body
                })
                print("Internal Briefing email sent to Sameer & Bigpond successfully.")
            except Exception as email_err:
                print(f"Resend Error (Sameer Internal): {email_err}")

            # 3. Send Branded Confirmation and Payment Link Email to the CLIENT
            try:
                client_email_body = f"""
                <div style="font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; background-color: #f4f4f4; padding: 30px; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border: 1px solid #e1e1e1; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                        <!-- Header -->
                        <div style="background-color: #1a1a1a; color: #ffffff; padding: 40px 30px; text-align: center; border-bottom: 4px solid #ffcc00;">
                            <h1 style="margin: 0; font-size: 18px; letter-spacing: 2px; text-transform: uppercase; font-weight: 700;">Sameer Babbar Advisory</h1>
                            <p style="margin: 8px 0 0 0; font-size: 10px; color: #ffcc00; text-transform: uppercase; letter-spacing: 1.5px; font-weight: bold;">Strategic Diagnostic Assessment</p>
                        </div>
                        
                        <!-- Content Body -->
                        <div style="padding: 35px 30px;">
                            <p style="font-size: 15px; line-height: 1.6; color: #222;">Dear {data.name},</p>
                            <p style="font-size: 15px; line-height: 1.6; color: #222;">Your Strategic Alignment Audit has been processed by our advisory concierge. A proprietary screening has been executed regarding your reported primary bottleneck.</p>
                            
                            <!-- Custom Diagnosis Narrative -->
                            <div style="background-color: #fafafa; border-left: 4px solid #1a1a1a; padding: 20px; font-size: 14px; line-height: 1.7; color: #333; margin: 25px 0; font-style: italic;">
                                "{diagnosis_html}"
                            </div>
                            
                            <p style="font-size: 15px; line-height: 1.6; color: #222; margin-bottom: 25px;">To secure your structural alignment session and access your customized diagnostic architecture, please finalize your booking via your private, secure portal links below:</p>
                            
                            <!-- Option A -->
                            <div style="border: 1px solid #eee; padding: 20px; background-color: #ffffff; margin-bottom: 20px; text-align: center;">
                                <h3 style="margin-top: 0; font-size: 14px; text-transform: uppercase; color: #1a1a1a; letter-spacing: 0.5px;">Path A: Full Strategic Diagnostic</h3>
                                <p style="font-size: 13px; color: #666; margin: 5px 0 15px 0;">1-Hour Full Strategic Alignment Session. Custom diagnostic report and action plan.</p>
                                <a href="{checkout_premium.url}" style="display: inline-block; padding: 12px 24px; background-color: #ffcc00; color: #000; text-decoration: none; font-weight: bold; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Book Full Session ($500)</a>
                            </div>
                            
                            <!-- Option B -->
                            <div style="border: 1px solid #eee; padding: 20px; background-color: #ffffff; text-align: center;">
                                <h3 style="margin-top: 0; font-size: 14px; text-transform: uppercase; color: #1a1a1a; letter-spacing: 0.5px;">Path B: 15-Minute Alignment Triage</h3>
                                <p style="font-size: 13px; color: #666; margin: 5px 0 15px 0;">Discovery Litmus Test to ensure mutual fit for an ongoing commitment.</p>
                                <a href="{checkout_triage.url}" style="display: inline-block; padding: 12px 24px; background-color: #ffffff; color: #000; border: 2px solid #000; text-decoration: none; font-weight: bold; font-size: 12px; text-transform: uppercase; letter-spacing: 0.5px;">Book Triage Session ($95)</a>
                            </div>
                            
                            <p style="font-size: 13px; line-height: 1.6; color: #777; margin-top: 30px; text-align: center; font-style: italic;">
                                True scale requires conviction. Invest decisively in your structural foundation, and give the market the opportunity to mirror your absolute conviction.
                            </p>
                        </div>
                        
                        <!-- Footer -->
                        <div style="background-color: #fafafa; border-top: 1px solid #eee; padding: 25px; text-align: center; font-size: 11px; color: #888; line-height: 1.5;">
                            This message is confidential and intended solely for the recipient.<br>
                            &copy; Sameer Babbar Advisory. All rights reserved.
                        </div>
                    </div>
                </div>
                """
                resend.Emails.send({
                    "from": "advisory@sameerbabbar.com",
                    "to": data.email,
                    "subject": f"🔒 Strategic Diagnostic Portal: {data.name}",
                    "html": client_email_body
                })
                print(f"Branded booking portal email sent to client ({data.email}) successfully.")
            except Exception as client_email_err:
                print(f"Resend Error (Client): {client_email_err}")
            
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
