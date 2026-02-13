
import os
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

# Scopes required for the app
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

CREDENTIALS_FILE = '/Users/gagegreg/Documents/rhub/backyardbrains.rs-workshop-google-sync/google_credentials.json'
TOKEN_FILE = 'token.json'

def main():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                print(f"Error: Credentials file not found at {CREDENTIALS_FILE}")
                print("Please ensure your OAuth 2.0 Client ID JSON is available.")
                return

            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            
            # Using console strategy for remote execution if needed, 
            # though locally it might try to open browser.
            # We'll use run_local_server which is standard for installed apps.
            # If running on a headless server, need to use console flow.
            # trying generic run_local_server first as user seems to be on a mac.
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            print(f"Token saved to {TOKEN_FILE}")

if __name__ == '__main__':
    main()
