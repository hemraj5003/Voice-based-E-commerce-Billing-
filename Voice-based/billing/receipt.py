from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from database.mongo import get_shop_info
from config import PDF_FILE

def build_receipt_text_dict(cart_dict: dict, user_id: str) -> str:
    shop = get_shop_info(user_id)

    lines = []
    lines.append("=" * 32)
    lines.append(shop.get("shop_name", "My Grocery Store"))
    lines.append(f"Phone: {shop.get('phone', '')}")
    if shop.get("address"):
        lines.append(shop["address"])
    lines.append("=" * 32)
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")

    for item in cart_dict.get("items", []):
        variant_str = f" ({item['variant']})" if item.get('variant') else ""
        lines.append(
            f"{item['display_name']}{variant_str} x {item['quantity']} = ₹{item['line_total']:.2f}"
        )

    lines.append("")
    lines.append("-" * 32)
    lines.append(f"Subtotal: ₹{cart_dict.get('subtotal', 0):.2f}")
    lines.append(f"GST (5%): ₹{cart_dict.get('gst', 0):.2f}")
    lines.append(f"TOTAL: ₹{cart_dict.get('total', 0):.2f}")
    lines.append("-" * 32)
    lines.append("Thank you for shopping!")

    return "\n".join(lines)


def generate_pdf_dict(cart_dict: dict, user_id: str) -> str:
    shop = get_shop_info(user_id)
    c = canvas.Canvas(str(PDF_FILE), pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, shop.get("shop_name", "My Grocery Store"))
    y -= 20

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Phone: {shop.get('phone', '')}")
    y -= 15
    if shop.get("address"):
        c.drawString(50, y, shop["address"])
        y -= 15

    c.drawString(50, y, datetime.now().strftime("%Y-%m-%d %H:%M"))
    y -= 25

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, y, "Item")
    c.drawString(260, y, "Qty")
    c.drawString(320, y, "Rate")
    c.drawString(400, y, "Total")
    y -= 12
    c.line(50, y, 520, y)
    y -= 18

    c.setFont("Helvetica", 10)
    for item in cart_dict.get("items", []):
        variant_str = f" ({item['variant']})" if item.get('variant') else ""
        disp_name = item.get('display_name', item.get('name', '')) + variant_str
        c.drawString(50, y, disp_name)
        c.drawString(260, y, str(item["quantity"]))
        c.drawString(320, y, f"₹{item['price']:.2f}")
        c.drawString(400, y, f"₹{item['line_total']:.2f}")
        y -= 18

        if y < 100:
            c.showPage()
            y = height - 50

    y -= 10
    c.line(50, y, 520, y)
    y -= 20

    c.setFont("Helvetica-Bold", 11)
    c.drawString(320, y, "Subtotal:")
    c.drawString(420, y, f"₹{cart_dict.get('subtotal', 0):.2f}")
    y -= 18
    c.drawString(320, y, "GST (5%):")
    c.drawString(420, y, f"₹{cart_dict.get('gst', 0):.2f}")
    y -= 18
    c.drawString(320, y, "TOTAL:")
    c.drawString(420, y, f"₹{cart_dict.get('total', 0):.2f}")

    c.save()
    return str(PDF_FILE)