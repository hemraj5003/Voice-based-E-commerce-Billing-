from pymongo import MongoClient
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from config import MONGO_URL, DB_NAME
from logger import get_logger
from bson.objectid import ObjectId

log = get_logger("MongoDB")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

users = db["users"]
shops = db["shops"]
products = db["products"]
temporary_products = db["temporary_products"]
bills = db["bills"]
chat_sessions = db["chat_sessions"]

DEFAULT_PRODUCTS = [
    {"name": "sugar", "price": 45, "unit": "kg"},
    {"name": "rice", "price": 60, "unit": "kg", "variants": [
        {"name": "Basmati", "price": 120},
        {"name": "Kolam", "price": 60},
        {"name": "Sona Masuri", "price": 75}
    ]},
    {"name": "atta", "price": 42, "unit": "kg"},
    {"name": "milk", "price": 30, "unit": "liter"},
    {"name": "banana", "price": 60, "unit": "dozen"},
    {"name": "apple", "price": 120, "unit": "kg"},
    {"name": "bread", "price": 40, "unit": "loaf"},
    {"name": "egg", "price": 7, "unit": "piece"},
    {"name": "oil", "price": 140, "unit": "liter"},
    {"name": "salt", "price": 25, "unit": "kg"},
    {"name": "tea", "price": 180, "unit": "250g"},
    {"name": "biscuit", "price": 30, "unit": "packet"},
    {"name": "maggi", "price": 14, "unit": "packet"},
    {"name": "tomato", "price": 40, "unit": "kg"},
    {"name": "onion", "price": 35, "unit": "kg"},
]

# --- USER AUTH ---
def create_user(name, email, password):
    if users.find_one({"email": email}):
        return False
    users.insert_one({
        "name": name,
        "email": email,
        "password_hash": generate_password_hash(password),
        "created_at": datetime.datetime.utcnow()
    })
    return True

def verify_user(email, password):
    user = users.find_one({"email": email})
    if user and check_password_hash(user["password_hash"], password):
        user["_id"] = str(user["_id"])
        # Do not return password hash
        user.pop("password_hash", None)
        return user
    return None

def get_user_by_id(user_id: str):
    user = users.find_one({"_id": ObjectId(user_id)})
    if user:
        user["_id"] = str(user["_id"])
        user.pop("password_hash", None)
    return user

# --- SHOP INFO ---
def get_shop_info(user_id: str) -> dict:
    data = shops.find_one({"user_id": user_id}, {"_id": 0})
    if not data:
        return {}
    return data

def save_shop_info(user_id: str, name: str, phone: str, address: str = "") -> dict:
    shops.update_one(
        {"user_id": user_id},
        {"$set": {
            "shop_name": name.strip(),
            "phone": phone.strip(),
            "address": address.strip(),
            "created_at": datetime.datetime.utcnow()
        }},
        upsert=True
    )
    # Seed default products for this new shop if no products exist
    shop_doc = shops.find_one({"user_id": user_id})
    shop_id = str(shop_doc["_id"])
    
    if products.count_documents({"shop_id": shop_id}) == 0:
        seed_shop_products(shop_id)
        
    return get_shop_info(user_id)

def get_shop_id(user_id: str):
    if not user_id:
        return None
    shop = shops.find_one({"user_id": user_id})
    if shop:
        return str(shop["_id"])
    return None

# --- PRODUCTS ---
def seed_shop_products(shop_id: str) -> None:
    to_insert = []
    for dp in DEFAULT_PRODUCTS:
        to_insert.append({
            "shop_id": shop_id,
            "name": dp["name"],
            "display_name": dp["name"].title(),
            "price": dp["price"],
            "unit": dp["unit"],
            "variants": [], # ['Basmati', 'Kolam', 'Sona Masuri'] - example
            "created_at": datetime.datetime.utcnow()
        })
    products.insert_many(to_insert)

def list_products(shop_id: str) -> list[dict]:
    items = []
    # Include main products
    for p in products.find({"shop_id": shop_id}, {"_id": 0}):
        items.append({
            "name": p.get("name", ""),
            "display_name": p.get("display_name", p.get("name", "")),
            "price": p.get("price", 0),
            "unit": p.get("unit", "piece"),
            "variants": p.get("variants", [])
        })
    # Include temporary products
    for p in temporary_products.find({"shop_id": shop_id}, {"_id": 0}):
        items.append({
            "name": p.get("name", ""),
            "display_name": p.get("display_name", p.get("name", "")),
            "price": p.get("price", 0),
            "unit": p.get("unit", "piece"),
            "variants": [],
            "is_temp": True
        })
    return items

def find_product(shop_id: str, name: str) -> dict | None:
    # Check main products
    p = products.find_one(
        {"shop_id": shop_id, "name": {"$regex": f"^{name}$", "$options": "i"}},
        {"_id": 0}
    )
    if p:
        return p
    # Check temporary products
    tp = temporary_products.find_one(
        {"shop_id": shop_id, "name": {"$regex": f"^{name}$", "$options": "i"}},
        {"_id": 0}
    )
    if tp:
        return tp
    return None

def record_product_usage(shop_id: str, name: str):
    tp = temporary_products.find_one({"shop_id": shop_id, "name": {"$regex": f"^{name}$", "$options": "i"}})
    if tp:
        temporary_products.update_one({"_id": tp["_id"]}, {"$inc": {"usage_count": 1}})

def check_and_add_as_variant(shop_id: str, name: str, price: float) -> bool:
    name_lower = name.strip().lower()
    items = list(products.find({"shop_id": shop_id}, {"_id": 0}))
    
    for ep in items:
        base_name = ep.get("name", "").lower()
        if not base_name or len(base_name) < 3 or base_name == name_lower:
            continue
            
        if name_lower.endswith(" " + base_name) or name_lower.startswith(base_name + " "):
            if name_lower.endswith(" " + base_name):
                variant_name = name_lower[:len(name_lower) - len(base_name)].strip()
            else:
                variant_name = name_lower[len(base_name):].strip()
                
            if add_product_variant(shop_id, base_name, variant_name, price):
                return True
    return False

def add_product(shop_id: str, name: str, price: float, unit: str = "piece", variants: list = None) -> None:
    existing = products.find_one({"shop_id": shop_id, "name": name.strip().lower()})
    if existing:
        return

    if check_and_add_as_variant(shop_id, name, price):
        return

    products.insert_one({
        "shop_id": shop_id,
        "name": name.strip().lower(),
        "display_name": name.strip().title(),
        "price": price,
        "unit": unit,
        "variants": variants or [],
        "created_at": datetime.datetime.utcnow()
    })

def add_product_variant(shop_id: str, base_product_name: str, variant_name: str, price: float) -> bool:
    res = products.update_one(
        {"shop_id": shop_id, "name": base_product_name.lower()},
        {"$push": {"variants": {"name": variant_name.title(), "price": float(price)}}}
    )
    return res.modified_count > 0

def update_product_price(shop_id: str, name: str, price: float, variant: str = None) -> bool:
    name_lower = name.strip().lower()
    price = float(price)

    if variant:
        res = products.update_one(
            {"shop_id": shop_id, "name": name_lower, "variants.name": variant},
            {"$set": {"variants.$.price": price}}
        )
        return res.modified_count > 0
    else:
        res = products.update_one(
            {"shop_id": shop_id, "name": name_lower},
            {"$set": {"price": price}}
        )
        if res.modified_count > 0:
            return True
        res = temporary_products.update_one(
            {"shop_id": shop_id, "name": name_lower},
            {"$set": {"price": price}}
        )
        return res.modified_count > 0

# --- TEMPORARY PRODUCTS ---
def add_temporary_product(shop_id: str, name: str, price: float, unit: str = "piece") -> None:
    name_clean = name.strip().lower()
    if find_product(shop_id, name_clean):
        return
        
    if check_and_add_as_variant(shop_id, name, price):
        return
        
    temporary_products.insert_one({
        "shop_id": shop_id,
        "name": name_clean,
        "display_name": name.strip().title(),
        "price": float(price),
        "unit": unit,
        "usage_count": 1,
        "status": "temporary",
        "expires_at": datetime.datetime.utcnow() + datetime.timedelta(days=2)
    })

def promote_temporary_products():
    now = datetime.datetime.utcnow()
    # Find products that have usage_count >= 2 AND expired
    cursor = temporary_products.find({"usage_count": {"$gte": 2}, "expires_at": {"$lte": now}})
    
    for tp in cursor:
        add_product(
            shop_id=tp["shop_id"],
            name=tp["name"],
            price=tp["price"],
            unit=tp["unit"]
        )
        temporary_products.delete_one({"_id": tp["_id"]})
        log.info("Promoted temp product %s for shop %s", tp["name"], tp["shop_id"])
        
    # Also delete expired temp products that weren't used enough
    deleted = temporary_products.delete_many({"expires_at": {"$lte": now}})
    if deleted.deleted_count > 0:
        log.info("Deleted %s expired temporary products", deleted.deleted_count)

# --- CHAT SESSIONS ---
def get_chat_session(shop_id: str):
    return chat_sessions.find_one({"shop_id": shop_id}, {"_id": 0})

def update_chat_session(shop_id: str, pending_action: str = None, pending_product: str = None, state: str = None):
    chat_sessions.update_one(
        {"shop_id": shop_id},
        {"$set": {
            "pending_action": pending_action,
            "pending_product": pending_product,
            "state": state,
            "updated_at": datetime.datetime.utcnow()
        }},
        upsert=True
    )

def clear_chat_session(shop_id: str):
    chat_sessions.delete_one({"shop_id": shop_id})

# --- BILLS ---
def save_bill(shop_id: str, cart_data: dict) -> str:
    res = bills.insert_one({
        "shop_id": shop_id,
        "items": cart_data["items"],
        "subtotal": cart_data["subtotal"],
        "gst": cart_data["gst"],
        "total": cart_data["total"],
        "created_at": datetime.datetime.utcnow()
    })
    return str(res.inserted_id)