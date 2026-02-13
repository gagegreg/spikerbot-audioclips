
import json
import os
import re
import difflib
from services.parser import ScriptParser, AudioMeta, ScriptSegment

def normalize_text(text):
    return re.sub(r'[^a-zA-Z0-9\s]', '', text).lower().strip()

def fuzzy_match(quote, script_text, threshold=0.6): # Default strict threshold
    n_quote = normalize_text(quote)
    n_text = normalize_text(script_text)
    
    # 1. Exact Inclusion (current logic)
    if n_quote in n_text:
        return True
    if n_text in n_quote and len(n_text) > 10:
        return True
        
    # 2. Difflib Ratio (Levenshtein-ish)
    if not n_quote or not n_text: return False
    
    # Check if quote is a significant part of text
    # SequenceMatcher is good generally
    matcher = difflib.SequenceMatcher(None, n_quote, n_text)
    match = matcher.find_longest_match(0, len(n_quote), 0, len(n_text))
    
    if match.size == 0: return False
    
    # Ratio of matched part to quote length
    matched_ratio = match.size / len(n_quote)
    
    return matched_ratio > threshold


def main():
    parser = ScriptParser() # Assume this is in path or copy paste logic if not
    
    # Load Data
    with open("data/script.txt", "r") as f:
        script_raw = f.read()
    
    # Simple Segment Parser (or import)
    # Re-implementing simplified parser to check logic
    segments = []
    current_section = "INTRO"
    for line in script_raw.split('\n'):
        line = line.strip()
        if not line: continue
        if line.startswith("SCENE") or line.startswith("SECTION") or line.startswith("INTRO"):
            current_section = line
            # Also create segment for header? No.
        else:
            # Check for Character
            char = None
            text = line
            if ":" in line and len(line.split(":")[0]) < 20 and line.split(":")[0].isupper():
                parts = line.split(":", 1)
                char = parts[0].strip()
                text = parts[1].strip()
            
            segments.append({"section": current_section, "character": char, "text": text})
            
    with open("data/metadata.json", "r") as f:
        rows = json.load(f)
    
    # Parse Metadata
    # Row 7 is Quote
    metas = []
    # Skip header
    for r in rows[1:]:
        if len(r) >= 5: # Ensure enough columns
            metas.append({"quote": r[4], "filename": r[0]})
            
    # Test Matching
    strict_count = 0
    fuzzy_count = 0
    missed = []
    
    for m in metas:
        found = False
        quote = m['quote']
        
        # Strict
        for s in segments:
            n_q = normalize_text(quote)
            n_s = normalize_text(s['text'])
            if n_q in n_s:
                strict_count += 1
                found = True
                break
        
        if not found:
            # Fuzzy
            best_score = 0
            best_seg = None
            
            for s in segments:
                if fuzzy_match(quote, s['text'], 0.6):
                    fuzzy_count += 1
                    found = True
                    print(f"[FUZZY MATCH] \nQ: {quote}\nS: {s['text']}\n")
                    break
        
        if not found:
            missed.append(quote)
            
    print(f" Strict Matches: {strict_count}")
    print(f" Fuzzy Matches: {fuzzy_count}")
    print(f" Missed: {len(missed)}")
    
    if len(missed) > 0:
        print("\nChange Threshold? Sample Missed:")
        for m in missed[:5]:
            print(f"- {m}")

if __name__ == "__main__":
    main()
