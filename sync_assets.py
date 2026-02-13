
import os
import json
import io
import time
from services.google_client import GoogleClient
from dump_data import extract_text_from_docx

# Configuration
DOC_ID = "1HEAMYnmLBK5jNb2NXQC15WQKK5bfKWnI"
FOLDER_ID = "142ocPoek3NDBmXb_Z65g_Vl1wF4PNyyR"
SHEET_ID = "1z6SoOdwh8d1GX0x2q29Lu2gpDqWnfMSMuiLC9XsL030"

DATA_DIR = "data"
AUDIO_DIR = "static/audio"

def ensure_dirs():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
    if not os.path.exists(AUDIO_DIR):
        os.makedirs(AUDIO_DIR)

def sync_script(client):
    print("Downloading Script...")
    try:
        content = client.get_file_content(DOC_ID)
        text = extract_text_from_docx(content)
        with open(os.path.join(DATA_DIR, 'script.txt'), 'w') as f:
            f.write(text)
        print("✅ Script saved to data/script.txt")
    except Exception as e:
        print(f"❌ Failed to sync script: {e}")

def sync_metadata(client):
    print("Downloading Metadata (Sheet)...")
    try:
        rows = client.get_sheet_values(SHEET_ID, "A1:E1000")
        with open(os.path.join(DATA_DIR, 'metadata.json'), 'w') as f:
            json.dump(rows, f, indent=2)
        print("✅ Metadata saved to data/metadata.json")
    except Exception as e:
        print(f"❌ Failed to sync metadata: {e}")

def sync_audio(client):
    print("Scanning Drive for Audio Files...")
    try:
        # Get all files (recursively if needed, but client check 'folder' mime)
        # We need a recursive list function essentially.
        
        # Simple recursion for now
        all_files = []
        folders_to_check = [FOLDER_ID]
        
        while folders_to_check:
            current_id = folders_to_check.pop(0)
            files = client.list_files_in_folder(current_id)
            for f in files:
                if f['mimeType'] == 'application/vnd.google-apps.folder':
                    folders_to_check.append(f['id'])
                elif 'audio' in f['mimeType'] or f['name'].upper().endswith(('.WAV', '.MP3')):
                    all_files.append(f)
        
        print(f"Found {len(all_files)} audio files in Drive.")
        
        # Download
        for idx, f in enumerate(all_files):
            # Clean filename logic (some seem to be folders named .WAV? No, we used files list)
            # dump_data showed "DJI...WAV" as FOLDER. 
            # Wait, if they are Folders, the audio is INSIDE them.
            # UPDATE: dump_data showed "DJI...WAV" mimeType='application/vnd.google-apps.folder'
            # So the recursor above SHOULD catch the files inside if they obey standard structure.
            
            # Use original name, sanitize?
            safe_name = f['name'].replace('/', '_')
            local_path = os.path.join(AUDIO_DIR, safe_name)
            
            if os.path.exists(local_path):
                print(f"[{idx+1}/{len(all_files)}] Skipping {safe_name} (Exists)")
                continue
            
            print(f"[{idx+1}/{len(all_files)}] Downloading {safe_name}...")
            content = client.get_file_content(f['id'])
            with open(local_path, 'wb') as audio_file:
                audio_file.write(content)
                
    except Exception as e:
        print(f"❌ Failed to sync audio: {e}")

def run_sync():
    """Runs the full sync process."""
    ensure_dirs()
    client = GoogleClient()
    
    print("Starting Sync...")
    sync_script(client)
    sync_metadata(client)
    # sync_audio(client) # Optional: syncing audio might take too long for a web request? 
    # User said "not syncing", likely referring to metadata/script updates. 
    # Audio syncing could timeout a web request. 
    # Let's include it for now but be aware.
    sync_audio(client)
    
    print("\n🎉 Sync Complete!")
    return {"status": "success"}

if __name__ == "__main__":
    run_sync()
