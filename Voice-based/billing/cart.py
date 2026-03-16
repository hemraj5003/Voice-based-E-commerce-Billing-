from database.mongo import find_product


class Cart:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add_item(self, name: str, quantity: int) -> bool:
        product = find_product(name)

        if not product:
            return False

        quantity = max(1, int(quantity))

        existing = next(
            (item for item in self.items if item["name"].lower() == product["name"].lower()),
            None
        )

        if existing:
            existing["quantity"] += quantity
            existing["line_total"] = round(existing["price"] * existing["quantity"], 2)
        else:
            self.items.append(
                {
                    "name": product["name"],
                    "price": float(product["price"]),
                    "unit": product.get("unit", "piece"),
                    "quantity": quantity,
                    "line_total": round(float(product["price"]) * quantity, 2),
                }
            )

        return True

    def remove_item(self, name: str) -> None:
        self.items = [
            item for item in self.items
            if item["name"].lower() != name.lower()
        ]

    def update_quantity(self, name: str, quantity: int) -> None:
        quantity = max(1, int(quantity))

        for item in self.items:
            if item["name"].lower() == name.lower():
                item["quantity"] = quantity
                item["line_total"] = round(item["price"] * item["quantity"], 2)
                break

    def clear(self) -> None:
        self.items = []

    def subtotal(self) -> float:
        return round(sum(item["line_total"] for item in self.items), 2)

    def gst(self) -> float:
        return round(self.subtotal() * 0.05, 2)

    def total(self) -> float:
        return round(self.subtotal() + self.gst(), 2)

    def to_dict(self) -> dict:
        return {
            "items": self.items,
            "subtotal": self.subtotal(),
            "gst": self.gst(),
            "total": self.total(),
        }