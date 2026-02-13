import os.path
import io
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from googleapiclient.errors import HttpError

# If modifying these scopes, delete the file token.json.
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/spreadsheets.readonly'
]

SERVICE_ACCOUNT_FILE = '/Users/gagegreg/Documents/rhub/api.backyardbrains.com/api.googlekey.json'

class GoogleClient:
    def __init__(self, service_account_path=SERVICE_ACCOUNT_FILE):
        self.creds = None
        if os.path.exists(service_account_path):
            self.creds = Credentials.from_service_account_file(service_account_path, scopes=SCOPES)
        else:
            raise Exception(f"Service account file not found at {service_account_path}")

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
