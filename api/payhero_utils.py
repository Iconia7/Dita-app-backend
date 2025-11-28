import os
import requests
from django.utils import timezone
from urllib3.exceptions import InsecureRequestWarning 
import urllib3 

# Suppress the warning (As per your code)
urllib3.disable_warnings(InsecureRequestWarning)

def initiate_payhero_push(phone_number, amount, external_reference):
    """
    Initiates an STK Push request using the PayHero API.
    """
    api_url = "https://backend.payhero.co.ke/api/v2/payments"
    
    # Ensure these are set in your environment variables or hardcoded for testing
    auth_header = 'Basic OUdjMEMxdk9xbGRWOHJFamR1Ykg6Y2FSOVI5b0NlR1FMQUtsbWlWbWZLa1A5NlZJUzY3M1N2b1JJampBaA=='
    channel_id = '3145'
    
    # Callback URL construction
    base_url = os.getenv('BACKEND_URL', 'https://dita-app-backend.onrender.com') 
    callback_url = f"{base_url}/api/mpesa/callback/"

    headers = {
        "Authorization": auth_header,  
        "Content-Type": "application/json"
    }
    
    payload = {
        "amount": float(amount),
        "phone_number": phone_number,
        "channel_id": int(channel_id),
        "provider": "m-pesa",
        "external_reference": external_reference,
        "callback_url": callback_url,
        "customer_name": "DITA Member"
    }

    try:
        # verify=False is needed for some third-party integrations as you noted
        response = requests.post(api_url, json=payload, headers=headers, verify=False)
        response.raise_for_status()
        
        return response.json()
        
    except requests.exceptions.RequestException as e:
        print(f"PayHero initiation error: {e.response.text if e.response else e}")
        return None