import os

import requests
import urllib3
from urllib3.exceptions import InsecureRequestWarning

# Suppress the warning (As per your code)
urllib3.disable_warnings(InsecureRequestWarning)


def initiate_payhero_push(phone_number, amount, external_reference):
    """
    Initiates an STK Push request using the PayHero API.
    """
    api_url = "https://backend.payhero.co.ke/api/v2/payments"

    # Ensure these are set in your environment variables or hardcoded for testing
    auth_header = os.getenv("AUTH_HEADER")
    channel_id = os.getenv("CHANNEL_ID")

    # Callback URL construction
    base_url = os.getenv("BACKEND_URL", "https://api.dita.co.ke")
    my_secret = os.getenv("PAYHERO_CALLBACK_SECRET")  # e.g., "super_long_random_string_123"
    callback_url = f"{base_url}/api/mpesa/callback/?token={my_secret}"

    headers = {"Authorization": auth_header, "Content-Type": "application/json"}

    payload = {
        "amount": float(amount),
        "phone_number": phone_number,
        "channel_id": int(channel_id),
        "provider": "m-pesa",
        "external_reference": external_reference,
        "callback_url": callback_url,
        "customer_name": "DITA Member",
    }

    try:
        # verify=False is needed for some third-party integrations as you noted
        response = requests.post(api_url, json=payload, headers=headers, verify=False)
        response.raise_for_status()

        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"PayHero initiation error: {e.response.text if e.response else e}")
        return None
