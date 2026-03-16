from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from billing.shop import get_shop
from config import PDF_FILE
from database.mongo import reduce_stock


def build_receipt_text(cart) -> str:
    shop = get_shop()

    lines = []
    lines.append("=" * 32)
    lines.append(shop.get("name", "My Grocery Store"))
    lines.append(f"Phone: {shop.get('phone', '')}")
    if shop.get("address"):
        lines.append(shop["address"])
    lines.append("=" * 32)
    lines.append(datetime.now().strftime("%Y-%m-%d %H:%M"))
    lines.append("")

    for item in cart.items:
        lines.append(
            f"{item['name']} x {item['quantity']} = ₹{item['line_total']:.2f}"
        )

    lines.append("")
    lines.append("-" * 32)
    lines.append(f"Subtotal: ₹{cart.subtotal():.2f}")
    lines.append(f"GST (5%): ₹{cart.gst():.2f}")
    lines.append(f"TOTAL: ₹{cart.total():.2f}")
    lines.append("-" * 32)
    lines.append("Thank you for shopping!")

    return "\n".join(lines)


def update_inventory(cart) -> None:
    for item in cart.items:
        reduce_stock(item["name"], item["quantity"])


def generate_pdf(cart) -> str:
    shop = get_shop()
    c = canvas.Canvas(str(PDF_FILE), pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, shop.get("name", "My Grocery Store"))
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
    for item in cart.items:
        c.drawString(50, y, item["name"])
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
    c.drawString(420, y, f"₹{cart.subtotal():.2f}")
    y -= 18
    c.drawString(320, y, "GST (5%):")
    c.drawString(420, y, f"₹{cart.gst():.2f}")
    y -= 18
    c.drawString(320, y, "TOTAL:")
    c.drawString(420, y, f"₹{cart.total():.2f}")

    c.save()
    return str(PDF_FILE)