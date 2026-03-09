
import os
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from services.parser import ScriptParser

# Auth & Session
from starlette.middleware.sessions import SessionMiddleware
from authlib.integrations.starlette_client import OAuth
from pydantic import BaseModel


import uvicorn

app = FastAPI(root_path="/audio")

# Session Middleware (Required for Auth0)
# In production, use a strong secret key from env
app.add_middleware(SessionMiddleware, secret_key="some-random-secret-key-for-dev")

# Mount static files
# Audio files are in static/audio
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

from fastapi.responses import RedirectResponse

# Globals
DATA_DIR = "data"
META_PATH = os.path.join(DATA_DIR, "metadata.json")
SHEET_DUMP_PATH = os.path.join(DATA_DIR, "../sheet_dump.json") # It's in root based on view_file? No, view_file showed it in root of scratch? 
# view_file for sheet_dump.json was /Users/gagegreg/Documents/rhub/scratch/audio_preview_app/sheet_dump.json
# main.py is in same dir.
SHEET_DUMP_PATH = "sheet_dump.json"
RATINGS_PATH = os.path.join(DATA_DIR, "ratings.json")
COLLECTIONS_PATH = os.path.join(DATA_DIR, "collections.json")
AUDIO_DIR = "static/audio"

# Auth0 Configuration
AUTH0_CLIENT_ID = "U4J672GKADXVh3ztoIhisWTEgbwIYZOv"
AUTH0_CLIENT_SECRET = "Xx2zo1O3sSrX0YBG2EFVovh1ME2ihXIPwIY9vEsusFIIDPz0MCHcVcSTtCsTK6p0"
AUTH0_DOMAIN = "login.backyardbrains.com"

oauth = OAuth()
oauth.register(
    "auth0",
    client_id=AUTH0_CLIENT_ID,
    client_secret=AUTH0_CLIENT_SECRET,
    client_kwargs={
        "scope": "openid profile email",
    },
    server_metadata_url=f"https://{AUTH0_DOMAIN}/.well-known/openid-configuration",
)

# Rating Models
class RatingRequest(BaseModel):
    filename: str
    rating: int = 0
    starred: bool = False

class ClipItem(BaseModel):
    filename: str
    person: str = ""
    section: str = ""
    quote: str = ""
    drive_url: str = ""
    trim_start: float = 0
    trim_end: float = 0

class CollectionCreate(BaseModel):
    name: str
    clips: List[ClipItem] = []
    is_public: bool = False

class CollectionUpdate(BaseModel):
    name: Optional[str] = None
    clips: Optional[List[ClipItem]] = None
    is_public: Optional[bool] = None

def get_ratings():
    if not os.path.exists(RATINGS_PATH):
        return {}
    with open(RATINGS_PATH, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def get_collections():
    if not os.path.exists(COLLECTIONS_PATH):
        return {}
    with open(COLLECTIONS_PATH, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_collections(data):
    with open(COLLECTIONS_PATH, 'w') as f:
        json.dump(data, f, indent=2)

def save_ratings(data):
    with open(RATINGS_PATH, 'w') as f:
        json.dump(data, f, indent=2)

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    user = request.session.get("user")
    
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

    # Extract unique speakers
    speakers = set()
    for takes in sorted_sections.values():
        for take in takes:
            if take.person:
                speakers.add(take.person)
    sorted_speakers = sorted(list(speakers))

    # Load Ratings
    all_ratings = get_ratings()
    
    # Enrich takes with ratings
    # Structure: sections -> list of takes. 
    # We need to map ratings to takes.
    # Ratings JSON: { filename: { user_email: { rating: X, starred: Y } } }
    # We want to show:
    # - Average rating? Or just MY rating?
    # - User wants "use that user to be able to rate and star"
    # So we should show the current user's rating/star status.
    
    user_email = user.get("email") if user else None
    
    # We can pass the raw ratings and handle in template, or inject into takes.
    # Injecting is cleaner for the template, but `take` is likely a NamedTuple or class from parser.
    # Let's pass a separate dictionary of { filename: { rating: X, starred: Y } } for the current user.
    
    user_ratings_map = {}
    if user_email and all_ratings:
        for fname, users_map in all_ratings.items():
            if user_email in users_map:
                user_ratings_map[fname] = users_map[user_email]

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "sections": sorted_sections,
        "speakers": sorted_speakers,
        "user": user,
        "user_ratings": user_ratings_map
    })

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
        
    return RedirectResponse(url="/audio/")

# --- Auth Routes ---

@app.get("/login")
async def login(request: Request):
    redirect_uri = request.url_for("auth")
    return await oauth.auth0.authorize_redirect(request, redirect_uri)

@app.get("/auth")
async def auth(request: Request):
    try:
        token = await oauth.auth0.authorize_access_token(request)
    except Exception as e:
        # Handle error (e.g. user cancelled)
        return RedirectResponse(url="/audio/")
        
    user = token.get("userinfo")
    if user:
        request.session["user"] = user
        
    return RedirectResponse(url="/audio/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/audio/")

# --- API Routes ---

@app.post("/api/rate")
async def rate_audio(request: Request, payload: RatingRequest):
    print(f"Received rating request: {payload}")
    user = request.session.get("user")
    if not user:
        print("User not authenticated in request.")
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    email = user.get("email")
    if not email:
        print("User email not found in session.")
        raise HTTPException(status_code=400, detail="User email not found")
        
    data = get_ratings()
    print(f"Current ratings data size: {len(data)}")
    
    if payload.filename not in data:
        data[payload.filename] = {}
        
    # Update user's rating/star
    # Merging logic: if rating is 0, maybe keep old rating? Or 0 means unrated?
    # User said "rate and star".
    
    if email not in data[payload.filename]:
        data[payload.filename][email] = {}
        
    user_entry = data[payload.filename][email]
    
    # We update what is provided.
    user_entry["rating"] = payload.rating
    user_entry["starred"] = payload.starred
    
    save_ratings(data)
    
    return {"status": "ok", "data": user_entry}

# --- Collection Routes ---

def _get_audio_library():
    """Build the full audio library from metadata + local files."""
    if not os.path.exists(META_PATH):
        return []
    with open(META_PATH, 'r') as f:
        meta_rows = json.load(f)
    parser = ScriptParser()
    audio_metas = parser.parse_sheet_rows(meta_rows)
    local_audio_files = []
    if os.path.exists(AUDIO_DIR):
        local_audio_files = os.listdir(AUDIO_DIR)
    sections = parser.organize_by_section(audio_metas, local_audio_files)
    return sections

@app.get("/collections", response_class=HTMLResponse)
async def collections_page(request: Request):
    user = request.session.get("user")
    sections = _get_audio_library()
    sorted_sections = dict(sorted(sections.items()))
    speakers = set()
    for takes in sorted_sections.values():
        for take in takes:
            if take.person:
                speakers.add(take.person)
    return templates.TemplateResponse("collections.html", {
        "request": request,
        "sections": sorted_sections,
        "speakers": sorted(list(speakers)),
        "user": user,
    })

@app.get("/collections/{collection_id}", response_class=HTMLResponse)
async def collection_edit_page(request: Request, collection_id: str):
    user = request.session.get("user")
    collections = get_collections()
    col = collections.get(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")

    user_email = user.get("email") if user else None
    is_owner = col.get("owner_email") == user_email
    if not col.get("is_public") and not is_owner:
        raise HTTPException(status_code=403, detail="Access denied")

    sections = _get_audio_library()
    sorted_sections = dict(sorted(sections.items()))
    speakers = set()
    for takes in sorted_sections.values():
        for take in takes:
            if take.person:
                speakers.add(take.person)

    return templates.TemplateResponse("collections.html", {
        "request": request,
        "sections": sorted_sections,
        "speakers": sorted(list(speakers)),
        "user": user,
        "collection": col,
        "is_owner": is_owner,
    })

@app.get("/shared/{share_token}", response_class=HTMLResponse)
async def shared_collection_page(request: Request, share_token: str):
    user = request.session.get("user")
    collections = get_collections()
    col = None
    for c in collections.values():
        if c.get("share_token") == share_token:
            col = c
            break
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    if not col.get("is_public"):
        raise HTTPException(status_code=403, detail="This collection is not public")

    sections = _get_audio_library()
    sorted_sections = dict(sorted(sections.items()))
    speakers = set()
    for takes in sorted_sections.values():
        for take in takes:
            if take.person:
                speakers.add(take.person)

    return templates.TemplateResponse("collections.html", {
        "request": request,
        "sections": sorted_sections,
        "speakers": sorted(list(speakers)),
        "user": user,
        "collection": col,
        "is_owner": False,
    })

@app.get("/api/collections")
async def api_list_collections(request: Request):
    user = request.session.get("user")
    email = user.get("email") if user else None
    collections = get_collections()
    result = []
    for cid, col in collections.items():
        if col.get("owner_email") == email or col.get("is_public"):
            result.append(col)
    result.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return result

@app.post("/api/collections")
async def api_create_collection(request: Request, payload: CollectionCreate):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    email = user.get("email")
    cid = str(uuid.uuid4())[:8]
    share_token = str(uuid.uuid4())[:12]
    now = datetime.now(timezone.utc).isoformat()
    col = {
        "id": cid,
        "name": payload.name,
        "owner_email": email,
        "owner_name": user.get("name", email),
        "created_at": now,
        "updated_at": now,
        "is_public": payload.is_public,
        "share_token": share_token,
        "clips": [c.model_dump() for c in payload.clips],
    }
    collections = get_collections()
    collections[cid] = col
    save_collections(collections)
    return col

@app.put("/api/collections/{collection_id}")
async def api_update_collection(request: Request, collection_id: str, payload: CollectionUpdate):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    collections = get_collections()
    col = collections.get(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    if col.get("owner_email") != user.get("email"):
        raise HTTPException(status_code=403, detail="Not the owner")
    if payload.name is not None:
        col["name"] = payload.name
    if payload.clips is not None:
        col["clips"] = [c.model_dump() for c in payload.clips]
    if payload.is_public is not None:
        col["is_public"] = payload.is_public
    col["updated_at"] = datetime.now(timezone.utc).isoformat()
    collections[collection_id] = col
    save_collections(collections)
    return col

@app.delete("/api/collections/{collection_id}")
async def api_delete_collection(request: Request, collection_id: str):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    collections = get_collections()
    col = collections.get(collection_id)
    if not col:
        raise HTTPException(status_code=404, detail="Collection not found")
    if col.get("owner_email") != user.get("email"):
        raise HTTPException(status_code=403, detail="Not the owner")
    del collections[collection_id]
    save_collections(collections)
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
