import os
import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# Try loading env from root or current dir
load_dotenv()
load_dotenv("../.env")

app = FastAPI()

# Enable CORS for local and production testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SubscribeRequest(BaseModel):
    email: str

@app.post("/api/subscribe")
async def subscribe(req: SubscribeRequest):
    email = req.email.strip()
    if not email:
        raise HTTPException(status_code=400, detail="Email is required.")
        
    api_key = os.getenv("RESEND_API_KEY")
    if not api_key:
        print("ERROR: RESEND_API_KEY not found in environment.")
        raise HTTPException(status_code=500, detail="Server configuration error: RESEND_API_KEY is missing.")

    # HTML welcome template matching Syncberg theme
    html_content = f"""
    <div style="font-family: 'Inter', -apple-system, sans-serif; background-color: #f5f2ec; padding: 40px 20px; text-align: center;">
      <div style="max-width: 500px; margin: 0 auto; background: #ffffff; border-radius: 16px; padding: 40px 30px; box-shadow: 0 10px 30px rgba(22, 27, 46, 0.05); border: 1px solid #e2e0da; text-align: left;">
        
        <!-- Logo -->
        <div style="text-align: center; margin-bottom: 30px;">
          <div style="display: inline-block; width: 44px; height: 44px; background: #161b2e; border-radius: 10px; line-height: 44px; color: #ffffff; font-size: 20px; font-weight: bold; text-align: center;">
            S
          </div>
          <h2 style="color: #161b2e; font-size: 22px; font-weight: 800; margin-top: 12px; margin-bottom: 0; letter-spacing: -0.5px;">Syncberg</h2>
        </div>

        <h3 style="color: #161b2e; font-size: 18px; font-weight: 700; margin-top: 0; margin-bottom: 12px;">You're on the list! 🎉</h3>
        
        <p style="color: #4a5568; font-size: 15px; line-height: 1.6; margin-bottom: 20px;">
          Thanks for joining the Syncberg beta waitlist. We are building a digital city designed for real, meaningful connections, and we're thrilled to have you with us from day one.
        </p>

        <p style="color: #4a5568; font-size: 15px; line-height: 1.6; margin-bottom: 30px;">
          We will send you details on how to access the beta version as soon as your slot is ready.
        </p>

        <hr style="border: none; border-top: 1px solid #ede9e1; margin-bottom: 25px;" />

        <div style="text-align: center;">
          <p style="color: #a0aec0; font-size: 12px; margin: 0;">
            &copy; 2026 Syncberg. All rights reserved.
          </p>
          <p style="color: #a0aec0; font-size: 11px; margin: 5px 0 0 0;">
            You received this because you requested early access to Syncberg.
          </p>
        </div>

      </div>
    </div>
    """

    resend_url = "https://api.resend.com/emails"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "from": "Syncberg <support@syncberg.com>",
        "to": [email],
        "subject": "Welcome to the Syncberg Beta! 🎉",
        "html": html_content
    }

    try:
        res = requests.post(resend_url, json=payload, headers=headers)
        if res.status_code not in (200, 201):
            err_body = res.json()
            print("Resend API error:", err_body)
            
            # If the domain is not verified, fallback to onboarding@resend.dev (useful for dev/testing)
            error_msg = err_body.get("message", "")
            if "domain" in error_msg.lower() or "unauthorized" in error_msg.lower() or "verify" in error_msg.lower():
                print("Domain not verified. Attempting fallback to onboarding@resend.dev...")
                payload["from"] = "Syncberg <onboarding@resend.dev>"
                fallback_res = requests.post(resend_url, json=payload, headers=headers)
                if fallback_res.status_code in (200, 201):
                    return {"success": True, "message": "Email sent using fallback address onboarding@resend.dev."}
                
                # If fallback also fails, raise the error
                err_body = fallback_res.json()
                print("Resend API fallback error:", err_body)

            raise HTTPException(status_code=res.status_code, detail=err_body.get("message", "Failed to send email via Resend."))
            
        return {"success": True, "message": "Email sent successfully."}
    except Exception as e:
        print("Error sending email:", str(e))
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
