import json
import re
import difflib
import requests

from config import OLLAMA_URL, OLLAMA_MODEL
from database.mongo import list_products
from logger import get_logger

log = get_logger("OllamaNLP")

HINDI_MAP = {
    "चीनी": "sugar",
    "चिनी": "sugar",
    "चावल": "rice",
    "दूध": "milk",
    "केला": "banana",
    "केले": "banana",
    "सेब": "apple",
    "आटा": "atta",
    "तेल": "oil",
    "नमक": "salt",
    "चाय": "tea",
    "बिस्कुट": "biscuit",
    "मैगी": "maggi",
    "टमाटर": "tomato",
    "प्याज": "onion",
    "प्याज़": "onion",
    "मूंग": "moong",
    "मूँग": "moong",
    "दाल": "dal",
}

NUMBER_WORDS = {
    "one": 1, "ek": 1, "एक": 1, "वन": 1,
    "two": 2, "do": 2, "दो": 2, "टू": 2,
    "three": 3, "teen": 3, "तीन": 3, "थ्री": 3,
    "four": 4, "char": 4, "चार": 4, "फोर": 4,
    "five": 5, "paanch": 5, "पांच": 5, "फाइव": 5, "फाईव": 5,
    "six": 6, "chhe": 6, "छह": 6, "सिक्स": 6,
    "seven": 7, "saat": 7, "सात": 7, "सेवन": 7,
    "eight": 8, "aath": 8, "आठ": 8, "एट": 8,
    "nine": 9, "nau": 9, "नौ": 9, "नाइन": 9, "नाईन": 9,
    "ten": 10, "das": 10, "दस": 10, "टेन": 10,
    "half": 1, "aadha": 1, "आधा": 1,
    "dozen": 12,
}


def normalize_text(text: str) -> str:
    t = text.lower().strip()

    for k, v in HINDI_MAP.items():
        t = t.replace(k, v)

    for k, v in NUMBER_WORDS.items():
        t = re.sub(rf"\b{re.escape(k)}\b", str(v), t)

    t = t.replace("kgs", "kg").replace("kilograms", "kg").replace("kilogram", "kg")
    t = t.replace("litres", "liter").replace("litre", "liter")
    return t


def best_product_match(shop_id: str, name: str) -> tuple[str, str|None]:
    target = name.lower().strip()
    products = list_products(shop_id)
    if not products:
        return target, None

    best_ratio = 0
    best_match = (target, None)
    
    for p in products:
        pname = p["name"].lower()
        if difflib.SequenceMatcher(None, target, pname).ratio() > best_ratio:
            best_ratio = difflib.SequenceMatcher(None, target, pname).ratio()
            best_match = (p["name"], None)
            
        for v in p.get("variants", []):
            vname = v.get("name", "") if isinstance(v, dict) else str(v)
            vname_lower = vname.lower()
            
            # Combine variant and product name (e.g. "basmati rice")
            r1 = difflib.SequenceMatcher(None, target, vname_lower).ratio()
            r2 = difflib.SequenceMatcher(None, target, f"{vname_lower} {pname}").ratio()
            r3 = difflib.SequenceMatcher(None, target, f"{pname} {vname_lower}").ratio()
            
            max_r = max(r1, r2, r3)
            # If the user speaks the variant, it takes precedence
            if max_r > best_ratio:
                best_ratio = max_r
                best_match = (p["name"], vname)
                
    if best_ratio >= 0.65:
        return best_match
    return target, None


def fallback_extract(shop_id: str, text: str) -> dict:
    text = normalize_text(text)
    items = []
    
    text = text.replace("1/2", "0.5").replace("1/4", "0.25").replace("3/4", "0.75")
    
    # Split by newline, comma, 'and', 'aur', or right before a numbered list item like " 1)" or " 2."
    segments = re.split(r'\n|,|\band\b|\baur\b|\s+(?=\d+[\)\.])', text)
    
    for segment in segments:
        segment = re.sub(r'^\s*[\d]+\s*[\)\.]\s*|^\s*-\s*', '', segment).strip()
        if not segment:
            continue
            
        tokens = re.findall(r"[a-zA-Z]+|\d+\.\d+|\d+", segment)
        name_parts = []
        qty = 1.0
        unit = None
        
        i = 0
        while i < len(tokens):
            if re.match(r"^\d+\.\d+$|^\d+$", tokens[i]):
                qty = float(tokens[i])
                if i + 1 < len(tokens) and tokens[i+1].lower() in {"kg", "liter", "gram", "gm", "ml", "packet", "piece", "dozen", "pkt", "littre", "g"}:
                    unit = tokens[i+1].lower()
                    if unit in ("gram", "g"): unit = "gm"
                    if unit == "littre": unit = "liter"
                    i += 1
            else:
                name_parts.append(tokens[i])
            i += 1
            
        if name_parts:
            candidate_str = " ".join(name_parts)
            candidate, variant = best_product_match(shop_id, candidate_str)
            items.append({"name": candidate, "quantity": qty, "variant": variant, "unit": unit})

    return {"items": items}


def extract_entities(text: str, shop_id: str) -> dict:
    clean_text = normalize_text(text)
    product_names = ", ".join(sorted({p["name"] for p in list_products(shop_id)}))

    prompt = f"""
You are a reliable product extraction parser.
Extract ALL requested items and their quantities (can be decimals/floats if needed) from the user text.
Also extract the `unit` (e.g. "kg", "gm", "liter", "ml", "piece", "packet", "pkt") if the user specifies one. 
Even if the item is not in the examples or is not a grocery item, extract it anyway!
The text may be in Hindi (Devanagari script), English, or a mix of both (Hinglish). 
CRITICAL RULES:
1. You MUST translate or transliterate ALL product names into English. DO NOT output any Devanagari/Hindi characters in the JSON values. Only use English letters.
2. DO NOT split multi-word product names into separate items. For example, "besan peda" or "paneer tikka" are single items. Do not extract them as two separate objects.
3. If the input is a numbered list (e.g., "1) item", "2. item"), IGNORE the list numbering. Do NOT parse the list bullet numbers as item quantities.
4. Correctly parse fraction terms: "1/2kg" = 0.5 kg, "1/4kg" = 0.25 kg, "3/4kg" = 0.75 kg.
5. Parse quantities attached directly to units or product names (e.g., "ghee500" -> quantity 500, "cake2pkt" -> quantity 2).
6. Include descriptive attributes in parentheses into the product name instead of dropping them (e.g. "Hand wash (pink ya purple)big").
7. RETAIN FULL product names, including brands, descriptors, and types (e.g., "Ashirwad Atta", "Wheat Powder", "Basmati Rice"). DO NOT drop brand names or adjectives. If the user says "Ashirwad Atta 2kg", extract "Ashirwad Atta", not just "Atta".

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

Existing product names (examples but not limited to):
{product_names}

Format:
{{
  "items": [
    {{"name": "sugar", "quantity": 1, "unit": "kg"}},
    {{"name": "cricket kit", "quantity": 1}},
    {{"name": "besan peda", "quantity": 2, "unit": "piece"}},
    {{"name": "paneer", "quantity": 0.5, "unit": "kg"}},
    {{"name": "atta", "quantity": 500, "unit": "gm"}}
  ]
}}

If nothing is found ONLY after carefully reading:
{{"items":[]}}

User text:
{clean_text}
"""

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }

    try:
        log.info("Sending text to Ollama")
        response = requests.post(OLLAMA_URL, json=payload, timeout=120)
        response.raise_for_status()

        raw = response.json().get("response", "").strip()
        print("OLLAMA RAW:", raw)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            log.warning("No JSON found in Ollama response, using fallback parser")
            return fallback_extract(shop_id, clean_text)

        data = json.loads(match.group())

        normalized = []
        for item in data.get("items", []):
            name = str(item.get("name", "")).strip().lower()
            try:
                qty = float(item.get("quantity", 1))
            except (ValueError, TypeError):
                qty = 1.0
                
            unit = item.get("unit")
            if unit:
                unit = str(unit).strip().lower()
                
            if not name:
                continue

            base_name, variant = best_product_match(shop_id, name)
            normalized.append({"name": base_name, "quantity": max(0.001, qty), "variant": variant, "unit": unit})

        return {"items": normalized}

    except Exception as e:
        log.error("Ollama parse failed: %s", e)
        return fallback_extract(shop_id, clean_text)