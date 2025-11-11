# app.py
from flask import Flask, request, jsonify, send_file, g
import sqlite3
from invoice import generate_invoice_pdf
import os, datetime, json

DATABASE = 'invoices.db'
UPLOAD_FOLDER = 'invoices'

app = Flask(__name__)

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def init_db():
    with app.app_context():
        cur = get_db().cursor()
        here = os.path.dirname(os.path.abspath(__file__))
        schema_path = os.path.join(here, 'schema.sql')
        if not os.path.exists(schema_path):
            raise FileNotFoundError("schema.sql not found")
        with open(schema_path, 'r', encoding='utf-8') as f:
            cur.executescript(f.read())
        get_db().commit()

# Index page with a simple HTML form for testing
@app.route("/", methods=["GET"])
def index():
    return """
    <h2>Invoice Generator API</h2>
    <p>Use the form below to create an invoice (simple demo).</p>
    <form id="inv" onsubmit="submitForm(event)">
      Customer name: <input id="customer_name" value="Swarup"><br>
      Customer email: <input id="customer_email" value="swarup@gmail.com"><br>
      Items JSON (example):<br>
      <textarea id="items" rows="6" cols="80">[{"description":"Widget A","qty":2,"unit_price":150.0},{"description":"Service B","qty":1,"unit_price":300.0}]</textarea><br>
      Tax (percent): <input id="tax" value="5"><br>
      <button type="submit">Create Invoice</button>
    </form>
    <pre id="out"></pre>
    <script>
    async function submitForm(e) {
      e.preventDefault();
      let itemsText = document.getElementById('items').value;
      let items = [];
      try { items = JSON.parse(itemsText); } catch (err) { alert('Invalid items JSON'); return; }
      const payload = {
        customer: { name: document.getElementById('customer_name').value, email: document.getElementById('customer_email').value },
        items: items,
        tax: parseFloat(document.getElementById('tax').value) || 0
      };
      const res = await fetch('/create_invoice', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const txt = await res.text();
      document.getElementById('out').textContent = txt;
    }
    </script>
    """, 200

# API: create invoice (accepts JSON)
@app.route('/create_invoice', methods=['POST'])
def create_invoice():
    # Accept JSON body
    if request.is_json:
        data = request.get_json()
    else:
        # fallback: try form fields (not used by JS but safe)
        try:
            data = {
                "customer": {"name": request.form.get('customer_name'), "email": request.form.get('customer_email')},
                "items": json.loads(request.form.get('items') or '[]'),
                "tax": float(request.form.get('tax') or 0)
            }
        except Exception:
            return jsonify({"error":"Invalid form data"}), 400

    if not data:
        return jsonify({"error":"JSON body required"}), 400

    # Basic validation
    items = data.get('items', [])
    if not isinstance(items, list) or len(items) == 0:
        return jsonify({"error":"items must be a non-empty list"}), 400

    # validate item fields
    for it in items:
        if 'description' not in it:
            return jsonify({"error":"each item must have a description"}), 400
        try:
            qty = float(it.get('qty', 1))
            unit = float(it.get('unit_price', 0))
        except Exception:
            return jsonify({"error":"qty and unit_price must be numbers"}), 400
        if qty < 0 or unit < 0:
            return jsonify({"error":"qty and unit_price must be non-negative"}), 400

    invoice_data = {
        "invoice_no": data.get("invoice_no"),
        "date": data.get("date", datetime.date.today().isoformat()),
        "customer": data.get("customer", {}),
        "items": items,
        "tax": data.get("tax", 0.0),
    }

    # Generate PDF
    try:
        pdf_path, subtotal, tax_amount, total = generate_invoice_pdf(invoice_data, outdir=UPLOAD_FOLDER)
    except Exception as e:
        return jsonify({"error":"Failed to generate PDF", "detail": str(e)}), 500

    # Insert into DB
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "INSERT INTO invoices (customer_name, customer_email,customer_mobile number, date, subtotal, tax, total, pdf_path) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (invoice_data['customer'].get('name'), invoice_data['customer'].get('email'),invoice_data['customer'].get('mobile number'),
         invoice_data['date'], subtotal, tax_amount, total, pdf_path)
    )
    invoice_id = cur.lastrowid
    for it in invoice_data['items']:
        cur.execute(
            "INSERT INTO invoice_items (invoice_id, description, qty, unit_price, line_total) VALUES (?,?,?,?,?)",
            (invoice_id, it.get('description'), it.get('qty'), it.get('unit_price'),
             float(it.get('qty',1))*float(it.get('unit_price',0)))
        )
    db.commit()

    return jsonify({"invoice_id": invoice_id, "pdf": pdf_path}), 201

# List invoices
@app.route('/invoices', methods=['GET'])
def list_invoices():
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, customer_name, date, total FROM invoices ORDER BY date DESC")
    rows = [dict(r) for r in cur.fetchall()]
    return jsonify(rows)

# Download PDF
@app.route('/invoice/<int:invoice_id>/pdf', methods=['GET'])
def download_invoice(invoice_id):
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT pdf_path FROM invoices WHERE id=?", (invoice_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({"error":"Invoice not found"}), 404
    path = row['pdf_path']
    if not os.path.exists(path):
        return jsonify({"error":"PDF not found on server"}), 404
    return send_file(path, as_attachment=True)

if __name__ == '__main__':
    if not os.path.exists(DATABASE):
        init_db()
    # Ensure invoices folder exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(host="127.0.0.1", port=5000, debug=True)
