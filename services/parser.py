
import re
from typing import List, Dict, Optional
from dataclasses import dataclass, field
import collections

@dataclass
class AudioMeta:
    filename: str
    person: str
    start: str
    stop: str
    section: str
    drive_url: str = ""

class ScriptParser:
    def __init__(self):
        pass

    def normalize_text(self, text: str) -> str:
        """Lowercases and removes punctuation for matching."""
        return re.sub(r'[^a-z0-9\s]', '', text.lower()).strip()

    def parse_sheet_rows(self, rows: List[List[str]]) -> List[AudioMeta]:
        """Parses raw sheet rows into AudioMeta objects."""
        metas = []
        # Header: File Name, Person, Start, Stop, Section
        # Skip Header
        for r in rows[1:]:
            if len(r) < 5: 
                continue
            
            meta = AudioMeta(
                filename=r[0],
                person=r[1],
                start=r[2],
                stop=r[3],
                section=r[4]
            )
            metas.append(meta)
        return metas

    def organize_by_section(self, audio_metas: List[AudioMeta], local_filenames: List[str]) -> Dict[str, List[AudioMeta]]:
        """
        1. Link AudioMeta to Local Files (get URLs).
        2. Group by Section.
        """
        
        # 1. Map filename -> local file
        def clean_name(n):
            return n.replace('.WAV.MP3', '').replace('.WAV', '').strip()

        local_map = {}
        for fname in local_filenames:
            local_map[clean_name(fname)] = fname

        # Grouping
        grouped = collections.defaultdict(list)

        for meta in audio_metas:
            cname = clean_name(meta.filename)
            if cname in local_map:
                actual_filename = local_map[cname]
                meta.drive_url = f"/static/audio/{actual_filename}"
                
                # Only add if we have the file? Or add anyway? 
                # User wants to preview, so we likely only want ones we have.
                grouped[meta.section].append(meta)
            else:
                # Keep it but mark as missing? Or skip.
                # Let's skip for now to keep UI clean.
                pass
                
        return grouped
