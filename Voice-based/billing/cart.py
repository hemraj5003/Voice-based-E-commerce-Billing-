from database.mongo import find_product, record_product_usage

def get_cart(session_dict: dict) -> list[dict]:
    if "cart_items" not in session_dict:
        session_dict["cart_items"] = []
    return session_dict["cart_items"]

def cart_payload(cart_items: list[dict]) -> dict:
    subtotal = round(sum(item["line_total"] for item in cart_items), 2)
    gst = round(subtotal * 0.05, 2)
    total = round(subtotal + gst, 2)
    return {
        "items": cart_items,
        "subtotal": subtotal,
        "gst": gst,
        "total": total
    }

def add_item(session_dict: dict, shop_id: str, name: str, quantity: float, variant: str = None, unit: str = None) -> bool:
    product = find_product(shop_id, name)
    if not product:
        return False
        
    quantity = max(0.001, float(quantity))
    
    # Handle unit conversion if spoken unit differs from base unit
    if unit and product.get("unit"):
        expected_unit = product.get("unit").lower()
        spoken_unit = unit.lower()
        
        weight_base = ["kg", "kilo", "kilogram", "kilograms"]
        weight_small = ["gm", "gram", "g", "grams"]
        vol_base = ["liter", "litre", "l", "liters"]
        vol_small = ["ml", "milliliter", "milliliters"]
        
        if spoken_unit in weight_small and expected_unit in weight_base:
            quantity = quantity / 1000.0
        elif spoken_unit in weight_base and expected_unit in weight_small:
            quantity = quantity * 1000.0
        elif spoken_unit in vol_small and expected_unit in vol_base:
            quantity = quantity / 1000.0
        elif spoken_unit in vol_base and expected_unit in vol_small:
            quantity = quantity * 1000.0
            
    cart_items = get_cart(session_dict)
    
    base_price = float(product["price"])
    item_price = base_price
    available_variants = product.get("variants", [])
    
    # If variants have specific prices, use it
    if available_variants and isinstance(available_variants[0], dict):
        if variant:
            for v in available_variants:
                if v.get("name") == variant:
                    item_price = float(v.get("price", base_price))
                    break
    
    existing = None
    for item in cart_items:
        if item["name"].lower() == product["name"].lower():
            if (item.get("variant") or "") == (variant or ""):
                existing = item
                break

    if existing:
        existing["quantity"] += quantity
        existing["line_total"] = round(existing["price"] * existing["quantity"], 2)
    else:
        cart_items.append({
            "name": product["name"],
            "display_name": product.get("display_name", product["name"]),
            "price": item_price,
            "base_price": base_price,
            "unit": product.get("unit", "piece"),
            "variant": variant,
            "quantity": quantity,
            "line_total": round(item_price * quantity, 2),
            "needs_variant": bool(product.get("variants")) and not variant,
            "available_variants": product.get("variants", [])
        })
        
    session_dict["cart_items"] = cart_items
    
    # Record usage for temporary products
    if product.get("status") == "temporary":
        record_product_usage(shop_id, product["name"])
        
    return True

def remove_item(session_dict: dict, name: str, variant: str = None) -> None:
    cart_items = get_cart(session_dict)
    new_items = []
    for item in cart_items:
        if item["name"].lower() == name.lower() and (item.get("variant") or "") == (variant or ""):
            continue
        new_items.append(item)
    session_dict["cart_items"] = new_items

def update_quantity(session_dict: dict, name: str, quantity: float, variant: str = None) -> None:
    quantity = max(0.001, float(quantity))
    cart_items = get_cart(session_dict)
    for item in cart_items:
        if item["name"].lower() == name.lower() and (item.get("variant") or "") == (variant or ""):
            item["quantity"] = quantity
            item["line_total"] = round(item["price"] * item["quantity"], 2)
            break
    session_dict["cart_items"] = cart_items

def update_variant(session_dict: dict, name: str, old_variant: str, new_variant: str) -> None:
    cart_items = get_cart(session_dict)
    for item in cart_items:
        if item["name"].lower() == name.lower() and (item.get("variant") or "") == (old_variant or ""):
            item["variant"] = new_variant if new_variant else None
            item["needs_variant"] = not bool(new_variant) and bool(item.get("available_variants"))
            
            # Reset to base price
            item["price"] = float(item.get("base_price", item.get("price", 0)))
            
            # Recalculate price if variant has custom price
            available_variants = item.get("available_variants", [])
            if available_variants and isinstance(available_variants[0], dict) and new_variant:
                for v in available_variants:
                    if str(v.get("name")) == str(new_variant):
                        item["price"] = float(v.get("price", item["price"]))
                        break
            
            item["line_total"] = round(item["price"] * item["quantity"], 2)
            break
    session_dict["cart_items"] = cart_items

def update_price(session_dict: dict, name: str, price: float, variant: str = None) -> None:
    cart_items = get_cart(session_dict)
    price = max(0.0, float(price))
    for item in cart_items:
        if item["name"].lower() == name.lower() and (item.get("variant") or "") == (variant or ""):
            item["price"] = price
            item["line_total"] = round(item["price"] * item["quantity"], 2)
            break
    session_dict["cart_items"] = cart_items

def clear_cart(session_dict: dict) -> None:
    session_dict["cart_items"] = []