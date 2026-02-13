import json
import zipfile
import xml.etree.ElementTree as ET
import io
from services.google_client import GoogleClient

DOC_ID = "1HEAMYnmLBK5jNb2NXQC15WQKK5bfKWnI"
FOLDER_ID = "142ocPoek3NDBmXb_Z65g_Vl1wF4PNyyR"

def extract_text_from_docx(docx_content):
    """Extract text from a DOCX file (byte string) by parsing XML."""
    try:
        with zipfile.ZipFile(io.BytesIO(docx_content)) as z:
            xml_content = z.read('word/document.xml')
            tree = ET.fromstring(xml_content)
            
            # XML namespace for Word
            namespaces = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
            
            text_parts = []
            for p in tree.findall('.//w:p', namespaces):
                # Paragraph
                paragraph_text = []
                for t in p.findall('.//w:t', namespaces):
                    if t.text:
                        paragraph_text.append(t.text)
                text_parts.append(''.join(paragraph_text))
            
            return '\n'.join(text_parts)
    except Exception as e:
        return f"Error parsing DOCX: {e}"

def main():
    client = GoogleClient()
    
    print("Fetching Script File (DOCX)...")
    try:
        content = client.get_file_content(DOC_ID)
        text = extract_text_from_docx(content)
        with open('script_text.txt', 'w') as f:
            f.write(text)
        print(f"Script text extracted to script_text.txt ({len(text)} chars)")
    except Exception as e:
        print(f"Failed to fetch script: {e}")
    
    print("Listing Files in Folder...")
    # ... rest of the file listing logic
    files = client.list_files_in_folder(FOLDER_ID)
    with open('files_dump.json', 'w') as f:
        json.dump(files, f, indent=2)
    print(f"File list saved to files_dump.json ({len(files)} files)")

    print("Fetching AudioCuts Sheet...")
    SHEET_ID = "1z6SoOdwh8d1GX0x2q29Lu2gpDqWnfMSMuiLC9XsL030"
    try:
        # Fetching first sheet, assuming data is there
        values = client.get_sheet_values(SHEET_ID, "A1:Z100") 
        with open('sheet_dump.json', 'w') as f:
            json.dump(values, f, indent=2)
        print(f"Sheet dump saved to sheet_dump.json ({len(values)} rows)")
    except Exception as e:
        print(f"Failed to fetch sheet: {e}")

if __name__ == '__main__':
    main()
