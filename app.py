from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from PIL import Image
import os, io, requests

app = Flask(__name__)
app.secret_key = "kfc_secret_key"

# ---------- Configuration ----------
kfc_name = "KFC"
city = "Kolkata, West Bengal"
location = "No 20 K Park street, Sir William Jones Sarani"
pincode = "700016"

# File paths
logo_path = "static/assets/kfc_logo.png"
bg_path = "static/assets/bg_kfc.png"

# Menu (same as your console app)
menu_prices = {
    "Zinger Burger": {"Regular": 85, "Big Size": 110, "Customize": 135},
    "Chicken Strips": {"Regular": 145, "Big Size": 195, "Customize": 235},
    "KFC Chicken": {"Regular": 290, "Big Size": 350, "Customize": 410},
    "Chicken Bowl": {"Regular": 295, "Big Size": 365, "Customize": 450},
}

# Ensure static asset folder exists
os.makedirs("static/assets", exist_ok=True)

# ---------- Utility functions ----------

def download_kfc_logo():
    """Downloads the KFC logo if missing"""
    if os.path.exists(logo_path):
        return
    try:
        url = "https://logos-world.net/wp-content/uploads/2020/04/KFC-Logo.png"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(logo_path, "wb") as f:
            f.write(r.content)
        img = Image.open(logo_path)
        img.verify()
        print("✓ KFC logo ready.")
    except Exception as e:
        print("⚠ Could not download KFC logo:", e)

def download_kfc_background():
    """Creates a faint KFC watermark background"""
    if os.path.exists(bg_path):
        return
    try:
        url = "https://logos-world.net/wp-content/uploads/2020/04/KFC-Logo.png"
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        with open(bg_path, "wb") as f:
            f.write(r.content)
        img = Image.open(bg_path).convert("RGBA")
        alpha = img.split()[3]
        alpha = alpha.point(lambda p: int(p * 0.15))  # 15% opacity
        img.putalpha(alpha)
        img.save(bg_path)
        print("✓ KFC background ready.")
    except Exception as e:
        print("⚠ Could not create KFC background:", e)

def register_fonts():
    """Registers fonts if available"""
    candidates = {
        "Arial": [
            r"C:\Windows\Fonts\arial.ttf",
            r"/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
        ],
        "Arial-Bold": [
            r"C:\Windows\Fonts\arialbd.ttf",
            r"/usr/share/fonts/truetype/msttcorefonts/Arial_Bold.ttf",
        ],
    }
    for name, paths in candidates.items():
        for p in paths:
            if os.path.exists(p):
                try:
                    pdfmetrics.registerFont(TTFont(name, p))
                    break
                except Exception:
                    pass

# Prepare resources
download_kfc_logo()
download_kfc_background()
register_fonts()

# ---------- PDF Generator ----------
def generate_pdf(order_list):
    """Creates PDF and returns it as BytesIO"""
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    total = sum(i["price"] for i in order_list)
    gst = total * 0.12
    final_total = total + gst
    now = datetime.now()
    timestamp = now.strftime("%d-%b-%Y %I:%M %p")

    left_margin = 50
    right_margin = width - 50
    y = height - 60

    # Draw background
    if os.path.exists(bg_path):
        c.saveState()
        c.drawImage(bg_path, (width - 400) / 2, (height - 400) / 2, 400, 400, mask='auto')
        c.restoreState()

    # Timestamp top-right
    c.setFont("Courier", 9)
    c.drawString(right_margin - c.stringWidth(timestamp, "Courier", 9), y + 5, timestamp)

    # Logo
    if os.path.exists(logo_path):
        c.drawImage(logo_path, (width - 150) / 2, y - 80, 150, 80, mask='auto')
        y -= 90
    else:
        c.setFont("Helvetica-Bold", 26)
        c.setFillColor(colors.red)
        c.drawCentredString(width / 2, y, kfc_name)
        y -= 34

    # Address
    c.setFont("Courier", 10)
    address = f"{city}, {location} - Pincode: {pincode}"
    c.drawCentredString(width / 2, y, address)
    y -= 25

    def line(ypos):
        c.setFont("Courier", 10)
        c.drawCentredString(width / 2, ypos, "-" * 85)
        return ypos - 20

    y = line(y)
    c.setFont("Courier-Bold", 11)
    c.drawString(left_margin, y, "ORDER DETAILS:")
    y -= 15
    y = line(y)

    # Items
    for idx, item in enumerate(order_list, start=1):
        if y < 100:
            c.showPage()
            y = height - 60
        c.setFont("Courier", 11)
        c.drawString(left_margin + 6, y, f"{idx}. {item['name']} - {item['size']}")
        price_txt = f"Rs. {item['price']}"
        c.drawString(right_margin - c.stringWidth(price_txt, "Courier", 11), y, price_txt)
        y -= 25

    y = line(y)
    c.setFont("Courier", 11)
    c.drawString(left_margin, y, "Total Order Value")
    c.drawString(right_margin - c.stringWidth(f"Rs. {total}", "Courier", 11), y, f"Rs. {total}")
    y -= 20

    y = line(y)
    c.setFont("Courier", 11)
    c.drawString(left_margin, y, "GST @12%")
    c.drawString(right_margin - c.stringWidth(f"Rs. {gst:.2f}", "Courier", 11), y, f"Rs. {gst:.2f}")
    y -= 20

    y = line(y)
    c.setFont("Courier-Bold", 12)
    c.drawString(left_margin, y, "FINAL AMOUNT (Including GST)")
    c.drawString(right_margin - c.stringWidth(f"Rs. {final_total:.2f}", "Courier-Bold", 12), y, f"Rs. {final_total:.2f}")
    y -= 40

    c.setFont("Courier-Bold", 11)
    c.drawCentredString(width / 2, y, "Thank you for ordering with KFC!")
    c.save()
    buffer.seek(0)
    return buffer

# ---------- Routes ----------

@app.route("/", methods=["GET"])
def index():
    """Show order form"""
    return render_template("index.html", menu=menu_prices)

@app.route("/generate", methods=["POST"])
def generate():
    """Receive order and return PDF"""
    names = request.form.getlist("item_name[]")
    sizes = request.form.getlist("item_size[]")
    qtys = request.form.getlist("item_qty[]")

    order_list = []
    for n, s, q in zip(names, sizes, qtys):
        if not n or not s:
            continue
        try:
            q = int(q)
            if q <= 0: continue
        except:
            continue
        price = menu_prices.get(n, {}).get(s)
        if price:
            for _ in range(q):
                order_list.append({"name": n, "size": s, "price": price})

    if not order_list:
        flash("Please add at least one valid item!", "error")
        return redirect(url_for("index"))

    pdf_buf = generate_pdf(order_list)
    filename = f"KFC_Bill_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    return send_file(pdf_buf, as_attachment=True, download_name=filename, mimetype="application/pdf")

# ---------- Main ----------
if __name__ == "__main__":
    print("🚀 Running KFC Billing App on http://127.0.0.1:5000")
    app.run(debug=True)
