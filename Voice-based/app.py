from flask import Flask, jsonify, request, render_template, send_file, session, redirect, url_for
from werkzeug.utils import secure_filename
from functools import wraps
import re


from stt.whisper import WhisperSTT
from nlp.ollama_nlp import extract_entities
from billing.cart import get_cart, cart_payload, add_item, remove_item, update_quantity, clear_cart, update_variant, update_price
from billing.receipt import build_receipt_text_dict, generate_pdf_dict
from database.mongo import (
    create_user, get_user_by_id, verify_user,
    get_shop_info, save_shop_info, get_shop_id,
    list_products, add_product, promote_temporary_products,
    add_temporary_product,
    get_chat_session, update_chat_session, clear_chat_session,
    save_bill, update_product_price
)
from config import AUDIO_FILE, UPLOAD_DIR
from logger import get_logger

app = Flask(__name__)
app.secret_key = "super_secret_voice_billing_key"
log = get_logger("App")

stt = WhisperSTT(model_size="base")

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

def shop_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Unauthorized"}), 401
        
        shop_id = get_shop_id(session["user_id"])
        if not shop_id:
            return jsonify({"error": "Shop not setup"}), 400
            
        kwargs["shop_id"] = shop_id
        return f(*args, **kwargs)
    return decorated_function

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login_page"))

# --- AUTH ROUTES ---
@app.route("/login", methods=["GET", "POST"])
def login_page():
    if request.method == "GET":
        return render_template("login.html")
        
    data = request.form
    user = verify_user(data.get("email"), data.get("password"))
    if user:
        session["user_id"] = user["_id"]
        return redirect(url_for("dashboard"))
    return render_template("login.html", error="Invalid credentials")

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "GET":
        return render_template("signup.html")
        
    data = request.form
    success = create_user(data.get("name"), data.get("email"), data.get("password"))
    if success:
        return redirect(url_for("login_page"))
    return render_template("signup.html", error="Email already exists")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login_page"))

# --- DASHBOARD & BILLING PAGES ---
@app.route("/dashboard")
@login_required
def dashboard():
    promote_temporary_products()
    shop = get_shop_info(session["user_id"])
    return render_template("dashboard.html", shop_exists=bool(shop))

@app.route("/billing")
@login_required
def billing_page():
    shop = get_shop_info(session["user_id"])
    if not shop:
        return redirect(url_for("dashboard"))
    return render_template("billing.html")

# --- SHOP ROUTES ---
@app.route("/shop", methods=["GET"])
@login_required
def get_shop_route():
    return jsonify(get_shop_info(session["user_id"]))

@app.route("/shop", methods=["POST"])
@login_required
def save_shop_route():
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()

    if not name or not phone:
        return jsonify({"error": "Shop name and phone required"}), 400

    shop_info = save_shop_info(session["user_id"], name, phone, address)
    return jsonify(shop_info)

# --- PRODUCT ROUTES ---
@app.route("/products", methods=["GET"])
@shop_required
def products_route(shop_id):
    return jsonify(list_products(shop_id))

@app.route("/products/add/voice", methods=["POST"])
@shop_required
def add_product_voice_route(shop_id):
    try:
        data = request.get_json(force=True)
        speech = str(data.get("speech", "")).strip().lower()
        if not speech:
            return jsonify({"error": "Empty speech"}), 400

        # Heuristic parser for adding product in English or Hindi
        # Example: "Add product milk price 30 per liter" or "प्रोडक्ट दूध भाव 30 लीटर"
        match = re.search(r"(?:add product|add item|add|नया प्रोडक्ट|प्रोडक्ट|आइटम)\s+(.+?)\s+(?:price|at|cost|भाव|रेट|कीमत)\s+(\d+)\s*(?:per|for|प्रति|का|रुपये|रूपये)?\s*((?:\d*\s*)?(?:kg|kilo|liter|litre|piece|packet|dozen|gram|gm|किलो|लीटर|पीस|पैकेट|दर्जन|ग्राम))?", speech)
        
        if match:
            name = match.group(1).strip()
            price = float(match.group(2))
            unit_raw = match.group(3) or "piece"
            unit_raw = unit_raw.strip()
            
            unit_map = {"किलो": "kg", "kilo": "kg", "लीटर": "liter", "litre": "liter", "पीस": "piece", "पैकेट": "packet", "दर्जन": "dozen", "ग्राम": "gram", "gm": "gm"}
            unit = unit_raw.lower()
            for hin, eng in unit_map.items():
                unit = re.sub(rf'\b{hin}\b', eng, unit)
                
            from database.mongo import list_products, add_product_variant
            existing_prods = list_products(shop_id)
            
            variant_added = False
            for ep in existing_prods:
                base_name = ep["name"].lower()
                # Check if "kolam rice" ends with " rice" or "rice kolam" starts with "rice "
                if name.lower().endswith(" " + base_name) or name.lower().startswith(base_name + " "):
                    if name.lower().endswith(" " + base_name):
                        variant_name = name[:len(name) - len(base_name)].strip()
                    else:
                        variant_name = name[len(base_name):].strip()
                        
                    variant_added = add_product_variant(shop_id, base_name, variant_name, price)
                    if variant_added:
                        return jsonify({"success": True, "message": f"Added variant '{variant_name.title()}' to '{base_name.title()}'", "product": {"name": base_name, "variant": variant_name, "price": price, "unit": ep.get("unit", unit)}})
            
            if not variant_added:
                add_product(shop_id, name, price, unit)
                return jsonify({"success": True, "message": f"Added new product '{name.title()}'", "product": {"name": name, "price": price, "unit": unit}})
                
        return jsonify({"error": "Could not parse product details. Say exactly: Add product [name] price [price] per [unit]  OR  प्रोडक्ट [name] भाव [price] [unit]"}), 400
    except Exception as e:
        log.error("add_product_voice fail: %s", e)
        return jsonify({"error": str(e)}), 500

# --- CART ROUTES ---
@app.route("/cart", methods=["GET"])
def get_cart_route():
    return jsonify(cart_payload(get_cart(session)))

@app.route("/cart/reset", methods=["POST"])
def reset_cart_route():
    clear_cart(session)
    return jsonify({"ok": True, "cart": cart_payload(get_cart(session))})

@app.route("/cart/update", methods=["POST"])
def cart_update_route():
    data = request.get_json(force=True)
    name = data.get("name", "")
    quantity = float(data.get("quantity", 1))
    variant = data.get("variant")
    update_quantity(session, name, quantity, variant)
    return jsonify(cart_payload(get_cart(session)))

@app.route("/cart/update_variant", methods=["POST"])
def cart_update_variant_route():
    data = request.get_json(force=True)
    name = data.get("name", "")
    old_variant = data.get("old_variant")
    new_variant = data.get("new_variant")
    update_variant(session, name, old_variant, new_variant)
    return jsonify(cart_payload(get_cart(session)))

@app.route("/cart/update_price", methods=["POST"])
@shop_required
def cart_update_price_route(shop_id):
    data = request.get_json(force=True)
    name = data.get("name", "")
    price = float(data.get("price", 0))
    variant = data.get("variant")
    update_price(session, name, price, variant)
    update_product_price(shop_id, name, price, variant)
    return jsonify(cart_payload(get_cart(session)))

@app.route("/cart/remove", methods=["POST"])
def cart_remove_route():
    data = request.get_json(force=True)
    name = data.get("name", "")
    variant = data.get("variant")
    remove_item(session, name, variant)
    return jsonify(cart_payload(get_cart(session)))

# --- BILLING/PROCESSING ---
@app.route("/process_text", methods=["POST"])
@shop_required
def process_text(shop_id):
    try:
        data = request.get_json(force=True)
        speech = str(data.get("speech", "")).strip()
        if not speech:
            return jsonify({"error": "Empty speech"}), 400

        print("🧠 Speech:", speech)
        entities = extract_entities(speech, shop_id)
        print("📦 Entities:", entities)

        added = []
        not_found = []

        for item in entities.get("items", []):
            ok = add_item(session, shop_id, item["name"], item["quantity"], item.get("variant"), item.get("unit"))
            if ok:
                added.append(item)
            else:
                not_found.append(item["name"])

        # Check if anything was missing to setup chat session
        chat_msg = None
        lang = "en-IN"
        if not_found:
            missing = not_found[0] # focus on first missing product
            update_chat_session(shop_id, pending_action="awaiting_confirm", pending_product=missing, state="initial")
            chat_msg = f"'{missing}' नहीं मिला। क्या मैं इसे आपके लिए जोड़ दूँ?"
            lang = "hi-IN"
        elif not added and speech.strip():
            chat_msg = "माफ़ करें, मुझे कोई आइटम समझ नहीं आया। कृप्या फिर से बताएं।"
            lang = "hi-IN"

        return jsonify({
            "speech": speech,
            "entities": entities,
            "added": added,
            "not_found": not_found,
            "cart": cart_payload(get_cart(session)),
            "chat_response": chat_msg,
            "lang": lang
        })

    except Exception as e:
        log.error("process_text failed: %s", e)
        return jsonify({"error": str(e)}), 500

@app.route("/chatbot/turn", methods=["POST"])
@shop_required
def chatbot_turn(shop_id):
    try:
        data = request.get_json(force=True)
        speech = str(data.get("speech", "")).strip().lower()
        
        chat_state = get_chat_session(shop_id)
        if not chat_state:
            return jsonify({"chat_response": "कोई सक्रिय चैट नहीं है।", "lang": "hi-IN"})
            
        action = chat_state.get("pending_action")
        prod = chat_state.get("pending_product")
        
        if action == "awaiting_confirm":
            if any(w in speech for w in ["yes", "haan", "add", "yup", "sure", "हाँ", "हां", "जी"]):
                update_chat_session(shop_id, pending_action="awaiting_price_unit", pending_product=prod)
                return jsonify({"chat_response": f"ठीक है। {prod} का भाव और वजन क्या है?", "lang": "hi-IN"})
            else:
                clear_chat_session(shop_id)
                return jsonify({"chat_response": f"ठीक है, {prod} को छोड़ रही हूँ।", "lang": "hi-IN"})
                
        elif action == "awaiting_price_unit":
            # Very simple parser. Wait for number + unit
            match = re.search(r"(\d+)\s*(kg|kilo|liter|piece|packet|dozen|gram|gm|किलो|लीटर|पीस|पैकेट|दर्जन|ग्राम)", speech)
            if match:
                price = float(match.group(1))
                unit_raw = match.group(2)
                unit_map = {"किलो": "kg", "kilo": "kg", "लीटर": "liter", "पीस": "piece", "पैकेट": "packet", "दर्जन": "dozen", "ग्राम": "gram", "gm": "gm"}
                unit = unit_map.get(unit_raw.lower(), unit_raw.lower())
            else:
                match_num = re.search(r"(\d+)", speech)
                if match_num:
                    price = float(match_num.group(1))
                    unit = "piece"
                else:
                    return jsonify({"chat_response": "मैं भाव नहीं समझ पाई। कृपया '50 किलो' की तरह बोलें।", "lang": "hi-IN"})
                    
            add_temporary_product(shop_id, prod, price, unit)
            # Add to cart immediately via session
            add_item(session, shop_id, prod, 1)
            
            clear_chat_session(shop_id)
            return jsonify({
                "chat_response": f"आइटम जुड़ गया! {prod} ₹{price}/{unit} के हिसाब से कार्ट में है।",
                "cart": cart_payload(get_cart(session)),
                "added_temp": True,
                "lang": "hi-IN"
            })
            
        return jsonify({"chat_response": "क्षमा करें, मुझे समझ नहीं आया।", "lang": "hi-IN"})
    except Exception as e:
        log.error("chatbot fail: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    try:
        file = request.files.get("audio")

        if not file:
            return jsonify({"error": "No audio file"}), 400

        filename = secure_filename(file.filename)
        path = UPLOAD_DIR / filename
        file.save(path)

        text = stt.transcribe(path)
        return jsonify({"speech": text})

    except Exception as e:
        log.error("upload_audio failed: %s", e)
        return jsonify({"error": str(e)}), 500

# --- BILL & RECEIPT ---
@app.route("/bill/preview", methods=["GET"])
@login_required
def bill_preview():
    cart_items_data = get_cart(session)
    cart_p = cart_payload(cart_items_data)
    
    receipt_txt = build_receipt_text_dict(cart_p, session["user_id"])
    
    return jsonify({
        "receipt_text": receipt_txt,
        "cart": cart_p
    })

@app.route("/generate_bill", methods=["POST"])
@shop_required
def generate_bill(shop_id):
    cart_items_data = get_cart(session)
    if not cart_items_data:
        return jsonify({"error": "Cart empty"}), 400

    cart_p = cart_payload(cart_items_data)
    save_bill(shop_id, cart_p) # Record to DB
    
    pdf_path = generate_pdf_dict(cart_p, session["user_id"])
    clear_cart(session)

    return send_file(pdf_path, as_attachment=True, download_name="receipt.pdf")

if __name__ == "__main__":
    print("🚀 Starting Multi-tenant Voice Billing SaaS")
    app.run(debug=True, port=5000, use_reloader=False)