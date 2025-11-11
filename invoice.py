from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
import datetime
import os

def generate_invoice_pdf(data, outdir="invoices"):
    """
    data: {
      invoice_no: optional string,
      date: optional (ISO string),
      customer: {"name": "...", "email": "..."},
      items: [ {"description": "...", "qty": number, "unit_price": number}, ... ],
      tax: percent (e.g. 5) or absolute number
    }
    returns: (path, subtotal, tax_amount, total)
    """
    os.makedirs(outdir, exist_ok=True)
    invoice_no = data.get("invoice_no") or f"INV{int(datetime.datetime.now().timestamp())}"
    filename = f"{invoice_no}.pdf"
    path = os.path.join(outdir, filename)

    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 20*mm

    # Header
    c.setFont("Helvetica-Bold", 18)
    c.drawString(margin, height - margin, "PAL INDUSTRIES")
    c.setFont("Helvetica", 9)
    c.drawString(margin, height - margin - 14, "37A,CHAWALPATTI LANE,BELEGHATA,KOLKATA-700010")
    c.drawString(margin, height - margin - 26, "palindustries@gmail.com")

    # Invoice meta (right)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(width - margin - 200, height - margin, "INVOICE")
    c.setFont("Helvetica", 9)
    c.drawString(width - margin - 200, height - margin - 18, f"Invoice No: {invoice_no}")
    c.drawString(width - margin - 200, height - margin - 32, f"Date: {data.get('date', datetime.date.today().isoformat())}")

    # Customer
    y = height - margin - 80
    c.setFont("Helvetica-Bold", 12)
    c.drawString(margin, y, "Bill To:")
    c.setFont("Helvetica", 9)
    customer = data.get("customer", {})
    c.drawString(margin, y - 14, customer.get("name", ""))
    c.drawString(margin, y - 28, customer.get("email", ""))

    # Table header
    y = y - 60
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Description")
    c.drawString(margin + 300, y, "Qty")
    c.drawString(margin + 350, y, "Unit Price")
    c.drawString(margin + 450, y, "Total")
    c.line(margin, y - 4, width - margin, y - 4)

    # Items
    c.setFont("Helvetica", 9)
    items = data.get("items", [])
    y = y - 18
    subtotal = 0.0
    for item in items:
        desc = str(item.get("description", ""))
        try:
            qty = float(item.get("qty", 1))
        except Exception:
            qty = 1.0
        try:
            unit = float(item.get("unit_price", 0.0))
        except Exception:
            unit = 0.0
        line_total = qty * unit
        subtotal += line_total

        c.drawString(margin, y, desc)
        c.drawRightString(margin + 330, y, str(int(qty)))
        c.drawRightString(margin + 440, y, f"{unit:.2f}")
        c.drawRightString(width - margin, y, f"{line_total:.2f}")
        y = y - 14
        if y < 100:
            c.showPage()
            y = height - margin - 40

    # Totals
    tax = data.get("tax", 0.0)
    tax_amount = 0.0
    try:
        tax_val = float(tax)
        if 0 < tax_val < 100:
            tax_amount = subtotal * (tax_val / 100.0)
        else:
            tax_amount = tax_val
    except Exception:
        tax_amount = 0.0
    total = subtotal + tax_amount

    y = y - 16
    c.line(margin, y, width - margin, y)
    y = y - 14
    c.drawRightString(width - margin - 100, y, "Subtotal:")
    c.drawRightString(width - margin, y, f"{subtotal:.2f}")
    y = y - 14
    c.drawRightString(width - margin - 100, y, "Tax:")
    c.drawRightString(width - margin, y, f"{tax_amount:.2f}")
    y = y - 14
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(width - margin - 100, y, "Total:")
    c.drawRightString(width - margin, y, f"{total:.2f}")

    c.showPage()
    c.save()
    return path, subtotal, tax_amount, total
