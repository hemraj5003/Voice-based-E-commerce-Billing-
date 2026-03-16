from flask import Flask, jsonify, request, render_template, send_file
from werkzeug.utils import secure_filename

from recorder.recorder import record
from stt.whisper import WhisperSTT
from nlp.ollama_nlp import extract_entities
from billing.cart import Cart
from billing.receipt import build_receipt_text, generate_pdf
from billing.shop import get_shop, save_shop
from database.mongo import seed_products, seed_shop, list_products
from config import AUDIO_FILE, UPLOAD_DIR
from logger import get_logger

app = Flask(__name__)
log = get_logger("App")

stt = WhisperSTT(model_size="base")
cart = Cart()


def cart_payload():
    return {
        "items": cart.items,
        "subtotal": cart.subtotal(),
        "gst": cart.gst(),
        "total": cart.total(),
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/products", methods=["GET"])
def products_route():
    return jsonify(list_products())


@app.route("/shop", methods=["GET"])
def get_shop_route():
    return jsonify(get_shop())


@app.route("/shop", methods=["POST"])
def save_shop_route():
    data = request.get_json(force=True)

    name = data.get("name", "").strip()
    phone = data.get("phone", "").strip()
    address = data.get("address", "").strip()

    if not name or not phone:
        return jsonify({"error": "Shop name and phone required"}), 400

    shop_info = save_shop(name, phone, address)
    return jsonify(shop_info)


@app.route("/cart", methods=["GET"])
def get_cart():
    return jsonify(cart_payload())


@app.route("/cart/reset", methods=["POST"])
def reset_cart():
    cart.clear()
    return jsonify({"ok": True, "cart": cart_payload()})


@app.route("/cart/update", methods=["POST"])
def cart_update():
    data = request.get_json(force=True)
    name = data.get("name", "")
    quantity = int(data.get("quantity", 1))

    cart.update_quantity(name, quantity)
    return jsonify(cart_payload())


@app.route("/cart/remove", methods=["POST"])
def cart_remove():
    data = request.get_json(force=True)
    name = data.get("name", "")

    cart.remove_item(name)
    return jsonify(cart_payload())


@app.route("/process_text", methods=["POST"])
def process_text():
    try:
        data = request.get_json(force=True)
        speech = str(data.get("speech", "")).strip()

        if not speech:
            return jsonify({"error": "Empty speech"}), 400

        print("🧠 Speech:", speech)

        entities = extract_entities(speech)

        print("📦 Entities:", entities)

        added = []
        not_found = []

        for item in entities.get("items", []):
            ok = cart.add_item(item["name"], item["quantity"])
            if ok:
                added.append(item)
            else:
                not_found.append(item["name"])

        return jsonify({
            "speech": speech,
            "entities": entities,
            "added": added,
            "not_found": not_found,
            "cart": cart_payload()
        })

    except Exception as e:
        log.error("process_text failed: %s", e)
        return jsonify({"error": str(e)}), 500


@app.route("/record", methods=["POST"])
def record_voice():
    try:
        print("🎤 Recording...")
        record()
        text = stt.transcribe(AUDIO_FILE)
        return process_text_internal(text)

    except Exception as e:
        log.error("record failed: %s", e)
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
        return process_text_internal(text)

    except Exception as e:
        log.error("upload_audio failed: %s", e)
        return jsonify({"error": str(e)}), 500


def process_text_internal(text):
    print("🧠 Speech:", text)

    entities = extract_entities(text)

    print("📦 Entities:", entities)

    added = []
    not_found = []

    for item in entities.get("items", []):
        ok = cart.add_item(item["name"], item["quantity"])
        if ok:
            added.append(item)
        else:
            not_found.append(item["name"])

    return jsonify({
        "speech": text,
        "entities": entities,
        "added": added,
        "not_found": not_found,
        "cart": cart_payload()
    })


@app.route("/bill/preview", methods=["GET"])
def bill_preview():
    return jsonify({
        "receipt_text": build_receipt_text(cart),
        "cart": cart_payload()
    })


@app.route("/generate_bill", methods=["POST"])
def generate_bill():
    if not cart.items:
        return jsonify({"error": "Cart empty"}), 400

    pdf_path = generate_pdf(cart)
    cart.clear()

    return send_file(pdf_path, as_attachment=True, download_name="receipt.pdf")


if __name__ == "__main__":
    print("🚀 Starting Voice Billing System")
    seed_products()
    seed_shop()
    app.run(debug=True)