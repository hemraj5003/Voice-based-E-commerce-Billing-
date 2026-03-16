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
}

NUMBER_WORDS = {
    "one": 1, "ek": 1, "एक": 1,
    "two": 2, "do": 2, "दो": 2,
    "three": 3, "teen": 3, "तीन": 3,
    "four": 4, "char": 4, "चार": 4,
    "five": 5, "paanch": 5, "पांच": 5,
    "six": 6, "chhe": 6, "छह": 6,
    "seven": 7, "saat": 7, "सात": 7,
    "eight": 8, "aath": 8, "आठ": 8,
    "nine": 9, "nau": 9, "नौ": 9,
    "ten": 10, "das": 10, "दस": 10,
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


def best_product_match(name: str) -> str:
    names = [p["name"] for p in list_products()]
    if not names:
        return name

    match = difflib.get_close_matches(name.lower().strip(), names, n=1, cutoff=0.65)
    return match[0] if match else name.lower().strip()


def fallback_extract(text: str) -> dict:
    text = normalize_text(text)
    tokens = re.findall(r"[a-zA-Z]+|\d+", text)

    items = []
    i = 0
    while i < len(tokens):
        if tokens[i].isdigit() and i + 1 < len(tokens):
            qty = int(tokens[i])
            candidate = tokens[i + 1]
            if candidate in {"kg", "liter", "gram", "packet", "piece", "dozen"} and i + 2 < len(tokens):
                candidate = tokens[i + 2]
                i += 1

            candidate = best_product_match(candidate)
            items.append({"name": candidate, "quantity": qty})
            i += 2
        else:
            i += 1

    return {"items": items}


def extract_entities(text: str) -> dict:
    clean_text = normalize_text(text)
    product_names = ", ".join(sorted({p["name"] for p in list_products()}))

    prompt = f"""
You are a grocery billing parser.
Extract grocery items and integer quantities from the user text.

Return ONLY valid JSON.
No explanation.
No markdown.
No extra text.

Allowed product names:
{product_names}

Format:
{{
  "items": [
    {{"name": "sugar", "quantity": 1}}
  ]
}}

If nothing is found:
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
        response = requests.post(OLLAMA_URL, json=payload, timeout=40)
        response.raise_for_status()

        raw = response.json().get("response", "").strip()
        print("OLLAMA RAW:", raw)

        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if not match:
            log.warning("No JSON found in Ollama response, using fallback parser")
            return fallback_extract(clean_text)

        data = json.loads(match.group())

        normalized = []
        for item in data.get("items", []):
            name = str(item.get("name", "")).strip().lower()
            qty = int(item.get("quantity", 1))
            if not name:
                continue

            name = best_product_match(name)
            normalized.append({"name": name, "quantity": max(1, qty)})

        return {"items": normalized}

    except Exception as e:
        log.error("Ollama parse failed: %s", e)
        return fallback_extract(clean_text)