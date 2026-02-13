
import os
import json
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
RATINGS_PATH = os.path.join(DATA_DIR, "ratings.json")
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

def get_ratings():
    if not os.path.exists(RATINGS_PATH):
        return {}
    with open(RATINGS_PATH, 'r') as f:
        try:
            return json.load(f)
        except:
            return {}

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
        
    return RedirectResponse(url=request.url_for("read_root"))

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
        return RedirectResponse(url="/")
        
    user = token.get("userinfo")
    if user:
        request.session["user"] = user
        
    return RedirectResponse(url="/")

@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse(url="/")

# --- API Routes ---

@app.post("/api/rate")
async def rate_audio(request: Request, payload: RatingRequest):
    user = request.session.get("user")
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    email = user.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="User email not found")
        
    data = get_ratings()
    
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

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
