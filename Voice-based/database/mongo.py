from pymongo import MongoClient
from config import MONGO_URL, DB_NAME
from logger import get_logger

log = get_logger("MongoDB")

client = MongoClient(MONGO_URL)
db = client[DB_NAME]

products = db["products"]
shop = db["shop"]


DEFAULT_PRODUCTS = [
    {"name": "sugar", "price": 45, "unit": "kg", "stock": 100},
    {"name": "rice", "price": 60, "unit": "kg", "stock": 100},
    {"name": "atta", "price": 42, "unit": "kg", "stock": 100},
    {"name": "milk", "price": 30, "unit": "liter", "stock": 100},
    {"name": "banana", "price": 60, "unit": "dozen", "stock": 100},
    {"name": "apple", "price": 120, "unit": "kg", "stock": 100},
    {"name": "bread", "price": 40, "unit": "loaf", "stock": 100},
    {"name": "egg", "price": 7, "unit": "piece", "stock": 300},
    {"name": "oil", "price": 140, "unit": "liter", "stock": 100},
    {"name": "salt", "price": 25, "unit": "kg", "stock": 100},
    {"name": "tea", "price": 180, "unit": "250g", "stock": 100},
    {"name": "biscuit", "price": 30, "unit": "packet", "stock": 100},
    {"name": "maggi", "price": 14, "unit": "packet", "stock": 100},
    {"name": "tomato", "price": 40, "unit": "kg", "stock": 100},
    {"name": "onion", "price": 35, "unit": "kg", "stock": 100},
]


def seed_products() -> None:
    if products.count_documents({}) == 0:
        products.insert_many(DEFAULT_PRODUCTS)
        log.info("Default products inserted")
    else:
        log.info("Products already exist")


def seed_shop() -> None:
    if shop.count_documents({}) == 0:
        shop.insert_one(
            {
                "name": "My Grocery Store",
                "phone": "0000000000",
                "address": "Nagpur",
            }
        )
        log.info("Default shop inserted")
    else:
        log.info("Shop already exists")


def normalize_products() -> None:
    updated = 0
    for p in products.find():
        updates = {}
        if "unit" not in p:
            updates["unit"] = "piece"
        if "stock" not in p:
            updates["stock"] = 100
        if updates:
            products.update_one({"_id": p["_id"]}, {"$set": updates})
            updated += 1

    if updated:
        log.info("Normalized %s old products", updated)


def list_products() -> list[dict]:
    items = []
    for p in products.find({}, {"_id": 0}):
        items.append(
            {
                "name": p.get("name", ""),
                "price": p.get("price", 0),
                "unit": p.get("unit", "piece"),
                "stock": p.get("stock", 0),
            }
        )
    return items


def find_product(name: str) -> dict | None:
    return products.find_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},
        {"_id": 0},
    )


def add_product(name: str, price: float, unit: str = "piece", stock: int = 100) -> None:
    existing = find_product(name)
    if existing:
        return

    products.insert_one(
        {
            "name": name.strip().lower(),
            "price": price,
            "unit": unit,
            "stock": stock,
        }
    )


def reduce_stock(name: str, quantity: int) -> None:
    products.update_one(
        {"name": {"$regex": f"^{name}$", "$options": "i"}},
        {"$inc": {"stock": -quantity}},
    )


def get_shop_info() -> dict:
    data = shop.find_one({}, {"_id": 0})
    if not data:
        return {"name": "My Grocery Store", "phone": "0000000000", "address": ""}
    return data


def save_shop_info(name: str, phone: str, address: str = "") -> dict:
    shop.delete_many({})
    shop.insert_one(
        {
            "name": name.strip(),
            "phone": phone.strip(),
            "address": address.strip(),
        }
    )
    return get_shop_info()


if __name__ == "__main__":
    print("🚀 MongoDB Connected")
    seed_products()
    seed_shop()
    normalize_products()

    print("\n📦 Product List:\n")
    for p in list_products():
        print(f"{p['name']} - ₹{p['price']}/{p['unit']} | Stock:{p['stock']}")