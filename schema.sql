CREATE TABLE IF NOT EXISTS invoices (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name TEXT,
    customer_email TEXT,
    date TEXT,
    subtotal REAL,
    tax REAL,
    total REAL,
    pdf_path TEXT
);

CREATE TABLE IF NOT EXISTS invoice_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    invoice_id INTEGER,
    description TEXT,
    qty INTEGER,
    unit_price REAL,
    line_total REAL,
    FOREIGN KEY(invoice_id) REFERENCES invoices(id)
);
