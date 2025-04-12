import os
import sys
import json
import webbrowser
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

GMAIL_CLIENT_ID = os.getenv("GMAIL_CLIENT_ID")
GMAIL_CLIENT_SECRET = os.getenv("GMAIL_CLIENT_SECRET")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
TOKEN_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "token.json"
)


def setup_auth():
    """Setup Gmail API authentication and get a refresh token."""
    if not GMAIL_CLIENT_ID or not GMAIL_CLIENT_SECRET:
        print("Error: GMAIL_CLIENT_ID and GMAIL_CLIENT_SECRET must be set in .env file")
        sys.exit(1)

    creds = None

    # Load existing credentials if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_info(
            json.loads(open(TOKEN_FILE).read()), SCOPES
        )

    # If no valid credentials, get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_config(
                {
                    "installed": {
                        "client_id": GMAIL_CLIENT_ID,
                        "client_secret": GMAIL_CLIENT_SECRET,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
                        "redirect_uris": [
                            "http://localhost",
                        ],
                    }
                },
                SCOPES,
            )
            creds = flow.run_local_server(port=8080)

        # Save the credentials for future use
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    # Print the refresh token for the user to add to .env
    refresh_token = creds.refresh_token

    print("\nAuthentication successful!")
    print("\nAdd the following to your .env file:")
    print(f"GMAIL_REFRESH_TOKEN={refresh_token}")

    return refresh_token


if __name__ == "__main__":
    setup_auth()
