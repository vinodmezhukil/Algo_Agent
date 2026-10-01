"""
Handles the Kite Connect login flow.

Kite's access tokens expire daily (around 6 AM IST), so this needs to
be re-run once a day, or wired into a scheduled job that runs before
market open. This flow can't be fully unattended because Zerodha's
login requires manual OTP/password authorization in a browser — there's
no way around that step for regulatory reasons.

Usage:
    python auth.py
This will print a login URL. Open it, log in, and Zerodha will redirect
to a URL containing a `request_token` parameter. Paste that back in
when prompted.
"""

from kiteconnect import KiteConnect
import config


def generate_session():
    kite = KiteConnect(api_key=config.API_KEY, timeout=15)
    print("Login URL (open in browser, log in, then copy the request_token")
    print("from the redirect URL's query params):\n")
    print(kite.login_url())

    request_token = input("\nPaste request_token here: ").strip()

    data = kite.generate_session(request_token, api_secret=config.API_SECRET)
    access_token = data["access_token"]

    with open(config.ACCESS_TOKEN_FILE, "w") as f:
        f.write(access_token)

    print(f"\nAccess token saved to {config.ACCESS_TOKEN_FILE}")
    print("This is valid until ~6 AM IST tomorrow.")


def get_kite_client():
    """Load a saved access token and return a ready-to-use KiteConnect client."""
    kite = KiteConnect(api_key=config.API_KEY)
    with open(config.ACCESS_TOKEN_FILE) as f:
        access_token = f.read().strip()
    kite.set_access_token(access_token)
    return kite


if __name__ == "__main__":
    generate_session()
