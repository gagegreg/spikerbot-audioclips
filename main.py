
import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.parser import ScriptParser

import uvicorn

app = FastAPI()

# Mount static files
# Audio files are in static/audio
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

from fastapi.responses import RedirectResponse

# Globals
DATA_DIR = "data"
META_PATH = os.path.join(DATA_DIR, "metadata.json")
AUDIO_DIR = "static/audio"

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    # 1. Load Metadata
    if not os.path.exists(META_PATH):
        return templates.TemplateResponse("index.html", {"request": request, "sections": {}, "error": "Metadata not found. Run sync."})
        
    with open(META_PATH, 'r') as f:
        meta_rows = json.load(f)
        
    # 2. Parse Metadata
    parser = ScriptParser()
    audio_metas = parser.parse_sheet_rows(meta_rows)
    
    # 3. List Local Audio Files
    local_audio_files = []
    if os.path.exists(AUDIO_DIR):
        local_audio_files = os.listdir(AUDIO_DIR)
        
    # 4. Organize by Section
    sections = parser.organize_by_section(audio_metas, local_audio_files)
    
    # Sort sections (optional, but good for consistent UI)
    sorted_sections = dict(sorted(sections.items()))

    return templates.TemplateResponse("index.html", {"request": request, "sections": sorted_sections})

from sync_assets import run_sync

@app.get("/refresh")
async def refresh_data(request: Request):
    print("Refresh triggered: running sync...")
    try:
        run_sync()
    except Exception as e:
        print(f"Error during manual sync: {e}")
        # Could return an error page/message, but redirecting to root 
        # will show old data or partial data, which is better than crash.
        pass
        
    return RedirectResponse(url=request.url_for("read_root"))

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
