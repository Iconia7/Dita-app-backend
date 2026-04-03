import base64
import logging
import os
from datetime import datetime

import requests
from django.conf import settings

logger = logging.getLogger(__name__)


def generate_access_token():
    """
    Generate Daraja Access Token using Consumer Key and Secret.
    """
    consumer_key = os.getenv("MPESA_CONSUMER_KEY")
    consumer_secret = os.getenv("MPESA_CONSUMER_SECRET")

    if not consumer_key or not consumer_secret:
        logger.error("M-Pesa Consumer Key/Secret missing in .env")
        return None

    api_url = "https://api.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials"

    try:
        response = requests.get(api_url, auth=(consumer_key, consumer_secret))
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        logger.exception(f"Error generating M-Pesa token: {e}")
        return None


def initiate_stk_push(phone_number, amount, external_reference):
    """
    Initiate STK Push (Lipa Na M-Pesa Online) using CustomerBuyGoodsOnline.
    """
    access_token = generate_access_token()
    if not access_token:
        return None

    shortcode = os.getenv("MPESA_SHORTCODE")
    passkey = os.getenv("MPESA_PASSKEY")
    till_number = os.getenv("MPESA_TILL_NUMBER")
    mpesa_secret = os.getenv("MPESA_CALLBACK_SECRET")
    backend_url = os.getenv("BACKEND_URL")
    # Unified Callback URL
    callback_url = f"{backend_url}/api/payments/mpesa/callback/?token={mpesa_secret}"

    # Safaricom Timestamp format: YYYYMMDDHHMMSS
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # Password generation (Base64 of Shortcode + Passkey + Timestamp)
    password_str = f"{shortcode}{passkey}{timestamp}"
    password = base64.b64encode(password_str.encode()).decode()

    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}

    payload = {
        "BusinessShortCode": shortcode,
        "Password": password,
        "Timestamp": timestamp,
        "TransactionType": "CustomerBuyGoodsOnline",  # 🟢 NEW: Direct Till Number
        "Amount": int(amount),
        "PartyA": phone_number,
        "PartyB": till_number,  # 🟢 NEW: The receiving Till Number
        "PhoneNumber": phone_number,
        "CallBackURL": callback_url,
        "AccountReference": external_reference[:12],  # Safaricom limit
        "TransactionDesc": "DITA Membership Payment",
    }

    try:
        api_url = "https://api.safaricom.co.ke/mpesa/stkpush/v1/processrequest"
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"M-Pesa STK Push error: {e.response.text if hasattr(e, 'response') else e}")
        return None
