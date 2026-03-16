from database.mongo import get_shop_info, save_shop_info

def get_shop() -> dict:
    return get_shop_info()

def save_shop(name: str, phone: str, address: str = "") -> dict:
    return save_shop_info(name, phone, address)