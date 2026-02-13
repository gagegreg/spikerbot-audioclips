
from services.google_client import GoogleClient

def main():
    client = GoogleClient()
    
    # Check Script File Metadata via Drive API
    script_id = "1HEAMYnmLBK5jNb2NXQC15WQKK5bfKWnI"
    print(f"Checking Script File Metadata ({script_id})...")
    try:
        file_meta = client.drive_service.files().get(
            fileId=script_id,
            fields="id, name, mimeType",
            supportsAllDrives=True
        ).execute()
        print(f"File Name: {file_meta['name']}")
        print(f"Mime Type: {file_meta['mimeType']}")
    except Exception as e:
        print(f"Error checking script file: {e}")

if __name__ == '__main__':
    main()
