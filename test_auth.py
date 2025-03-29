import os
import json
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_gmail_auth():
    """Test Gmail API authentication with refresh token."""
    client_id = os.getenv("GMAIL_CLIENT_ID")
    client_secret = os.getenv("GMAIL_CLIENT_SECRET")
    refresh_token = os.getenv("GMAIL_REFRESH_TOKEN")
    
    print(f"Client ID: {'Present' if client_id else 'Missing'}")
    print(f"Client Secret: {'Present' if client_secret else 'Missing'}")
    print(f"Refresh Token: {'Present' if refresh_token else 'Missing'}")
    
    if not all([client_id, client_secret, refresh_token]):
        raise ValueError("Missing Gmail API credentials in .env file")
    
    try:
        # Create credentials
        creds = Credentials(
            None,  # No token initially
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=client_id,
            client_secret=client_secret,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"]
        )
        
        # Always refresh regardless of expiration
        print("Refreshing token...")
        creds.refresh(Request())
        
        # Save the new access token for debugging
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "scopes": creds.scopes
        }
        print(f"Token refreshed successfully: {bool(creds.token)}")
        
        # Try a simple API call to verify
        service = build("gmail", "v1", credentials=creds)
        profile = service.users().getProfile(userId="me").execute()
        print(f"Authenticated as: {profile.get('emailAddress')}")
        
        return True
    except Exception as e:
        print(f"Authentication error: {str(e)}")
        if hasattr(e, 'args') and len(e.args) > 1:
            print(f"Error details: {e.args[1]}")
        return False

if __name__ == "__main__":
    test_gmail_auth()