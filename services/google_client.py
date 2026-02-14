import os.path
import io
import json
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.oauth2.credentials import Credentials as UserCredentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly'
]

# Use relative path for production/portability
SERVICE_ACCOUNT_FILE = 'api.googlekey.json'
TOKEN_FILE = 'token.json'

class GoogleClient:
    def __init__(self, service_account_path=None):
        self.creds = None
        
        # 1. Try Token (User OAuth)
        if os.path.exists(TOKEN_FILE):
            print(f"Loading credentials from {TOKEN_FILE}...")
            try:
                self.creds = UserCredentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            except Exception as e:
                print(f"Error loading token.json: {e}")

        # 1b. Refresh if needed
        if self.creds and self.creds.expired and self.creds.refresh_token:
            print("Refreshing token...")
            try:
                self.creds.refresh(Request())
                # Save refreshed token?
                with open(TOKEN_FILE, 'w') as token:
                    token.write(self.creds.to_json())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                self.creds = None
        
        # 2. Try Service Account if no valid user creds
        if not self.creds or not self.creds.valid:
            # If no path provided, use default relative path
            if not service_account_path:
                service_account_path = SERVICE_ACCOUNT_FILE
                
            # Check current dir or parent dirs (helpful for development flexibility)
            if not os.path.exists(service_account_path):
                 if os.path.exists(os.path.join("..", service_account_path)):
                     service_account_path = os.path.join("..", service_account_path)
            
            if os.path.exists(service_account_path):
                print(f"Loading service account from {service_account_path}...")
                self.creds = ServiceAccountCredentials.from_service_account_file(service_account_path, scopes=SCOPES)
            else:
                # Only raise if we simply have NO creds at all
                if not self.creds: # Double check
                     raise Exception(f"No credentials found. Missing {TOKEN_FILE} or {SERVICE_ACCOUNT_FILE}")

        self.docs_service = build('docs', 'v1', credentials=self.creds)
        self.drive_service = build('drive', 'v3', credentials=self.creds)
        self.sheets_service = build('sheets', 'v4', credentials=self.creds)

    def get_document(self, document_id):
        """Retrieve a Google Doc."""
        try:
            document = self.docs_service.documents().get(documentId=document_id).execute()
            return document
        except HttpError as err:
            print(err)
            return None

    def get_sheet_values(self, spreadsheet_id, range_name):
        """Retrieve values from a Google Sheet."""
        try:
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name).execute()
            return result.get('values', [])
        except HttpError as err:
            print(err)
            return []

    def list_files_in_folder(self, folder_id):
        """List files in a specific Google Drive folder."""
        files = []
        page_token = None
        try:
            while True:
                response = self.drive_service.files().list(
                    q=f"'{folder_id}' in parents and trashed = false",
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, webContentLink)',
                    pageToken=page_token,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True
                ).execute()
                
                files.extend(response.get('files', []))
                page_token = response.get('nextPageToken', None)
                if page_token is None:
                    break
            return files
        except HttpError as err:
            print(err)
            return []

    def get_file_content(self, file_id):
        """Download a file's content."""
        request = self.drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()

    def export_file(self, file_id, mime_type):
        """Export a Google Doc/Sheet to a specific MIME type."""
        request = self.drive_service.files().export_media(fileId=file_id, mimeType=mime_type)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while done is False:
            status, done = downloader.next_chunk()
        return fh.getvalue()
