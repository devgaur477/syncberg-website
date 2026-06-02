import os
import json
import requests
import firebase_admin
from firebase_admin import credentials, firestore

def send_welcome_email(email, api_key):
    # HTML welcome template matching Syncberg's theme
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
            error_msg = err_body.get("message", "")
            
            # Fallback to onboarding@resend.dev if domain not verified (good for testing)
            if "domain" in error_msg.lower() or "unauthorized" in error_msg.lower() or "verify" in error_msg.lower():
                print(f"Domain not verified. Trying fallback sender onboarding@resend.dev for {email}...")
                payload["from"] = "Syncberg <onboarding@resend.dev>"
                fallback_res = requests.post(resend_url, json=payload, headers=headers)
                if fallback_res.status_code in (200, 201):
                    return True, "sent (fallback)"
                err_body = fallback_res.json()
                
            return False, err_body.get("message", f"HTTP {res.status_code}")
        return True, "sent"
    except Exception as e:
        return False, str(e)

def main():
    print("Starting Syncberg email dispatcher cron job...")
    
    # 1. Load configuration
    resend_api_key = os.getenv("RESEND_API_KEY")
    service_account_str = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")
    
    if not resend_api_key:
        print("ERROR: RESEND_API_KEY env variable not set.")
        return
        
    # 2. Initialize Firebase
    try:
        if service_account_str:
            service_account_info = json.loads(service_account_str)
            cred = credentials.Certificate(service_account_info)
        elif os.path.exists("serviceAccountKey.json"):
            print("Found local serviceAccountKey.json file. Using it for initialization.")
            cred = credentials.Certificate("serviceAccountKey.json")
        elif os.path.exists("scripts/serviceAccountKey.json"):
            print("Found local scripts/serviceAccountKey.json file. Using it for initialization.")
            cred = credentials.Certificate("scripts/serviceAccountKey.json")
        else:
            print("ERROR: FIREBASE_SERVICE_ACCOUNT_JSON env variable not set and no local serviceAccountKey.json found.")
            return
            
        firebase_admin.initialize_app(cred)
    except Exception as e:
        print(f"ERROR: Failed to initialize Firebase SDK: {str(e)}")
        return

    db = firestore.client()
    
    # 3. Query Firestore waitlist where email_sent is False
    try:
        docs = db.collection("waitlist").where("email_sent", "==", False).stream()
        waitlist_entries = list(docs)
    except Exception as e:
        print(f"ERROR: Failed to query Firestore: {str(e)}")
        return

    if not waitlist_entries:
        print("No pending waitlist emails to send. Exiting.")
        return

    print(f"Found {len(waitlist_entries)} pending emails to send.")

    # 4. Process entries
    success_count = 0
    fail_count = 0

    for doc in waitlist_entries:
        doc_data = doc.to_dict()
        email = doc_data.get("email")
        
        if not email:
            print(f"Skipping document {doc.id}: no email address field.")
            continue
            
        print(f"Sending welcome email to {email}...")
        success, message = send_welcome_email(email, resend_api_key)
        
        if success:
            try:
                # Update Firestore document status
                doc.reference.update({
                    "email_sent": True,
                    "sent_at": firestore.SERVER_TIMESTAMP
                })
                print(f"SUCCESS: Email sent to {email} ({message}). Updated status in database.")
                success_count += 1
            except Exception as e:
                print(f"ERROR: Email was sent to {email} but failed to update status in Firestore: {str(e)}")
                fail_count += 1
        else:
            print(f"FAILED: Could not send email to {email}. Error: {message}")
            fail_count += 1

    print(f"Job finished. Successfully processed: {success_count}. Failed: {fail_count}.")

if __name__ == "__main__":
    main()
