"""Servidor web y API de devoluciones de Mercado Viva.

Ejecutar: python app.py
Abrir:     http://localhost:8000
"""
import json
import sqlite3
from datetime import datetime
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "mercado_viva.db"
ALLOWED_CATEGORY = "Tecnología"
STATUSES = {"Pendiente", "Aprobada", "Rechazada", "Procesada"}


def connection():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    return db


def initialize_database():
    with connection() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS return_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                order_number TEXT NOT NULL,
                email TEXT NOT NULL,
                product TEXT NOT NULL,
                category TEXT NOT NULL,
                reason TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Pendiente',
                created_at TEXT NOT NULL
            )
        """)
        count = db.execute("SELECT COUNT(*) FROM return_requests").fetchone()[0]
        if count == 0:
            now = datetime.now().isoformat(timespec="seconds")
            db.executemany("""
                INSERT INTO return_requests
                (code, order_number, email, product, category, reason, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                ("DV-2401", "MV-100842", "camila@email.com", "Audífonos inalámbricos", "Tecnología", "Producto defectuoso", "Pendiente", now),
                ("DV-2402", "MV-100516", "juan@email.com", "Teclado mecánico", "Tecnología", "No cumple mis expectativas", "Aprobada", now),
            ])


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", 0))
        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

    def do_GET(self):
        if urlparse(self.path).path == "/api/returns":
            with connection() as db:
                rows = db.execute("SELECT * FROM return_requests ORDER BY id DESC").fetchall()
            return self.send_json([dict(row) for row in rows])
        return super().do_GET()

    def do_POST(self):
        if urlparse(self.path).path != "/api/returns":
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = self.read_json()
        required = ("order_number", "email", "product", "category", "reason")
        if not data or any(not str(data.get(field, "")).strip() for field in required):
            return self.send_json({"error": "Completa todos los campos obligatorios."}, HTTPStatus.BAD_REQUEST)
        if data["category"] != ALLOWED_CATEGORY:
            return self.send_json({"error": "Solo se aceptan devoluciones de productos tecnológicos."}, HTTPStatus.UNPROCESSABLE_ENTITY)
        created_at = datetime.now().isoformat(timespec="seconds")
        with connection() as db:
            cursor = db.execute("""
                INSERT INTO return_requests
                (code, order_number, email, product, category, reason, status, created_at)
                VALUES ('TEMP', ?, ?, ?, ?, ?, 'Pendiente', ?)
            """, (data["order_number"].strip(), data["email"].strip(), data["product"].strip(), data["category"], data["reason"], created_at))
            request_id = cursor.lastrowid
            code = f"DV-{request_id:05d}"
            db.execute("UPDATE return_requests SET code = ? WHERE id = ?", (code, request_id))
            row = db.execute("SELECT * FROM return_requests WHERE id = ?", (request_id,)).fetchone()
        return self.send_json(dict(row), HTTPStatus.CREATED)

    def do_PATCH(self):
        parts = urlparse(self.path).path.strip("/").split("/")
        if len(parts) != 3 or parts[:2] != ["api", "returns"] or not parts[2].isdigit():
            return self.send_error(HTTPStatus.NOT_FOUND)
        data = self.read_json()
        status = data.get("status") if data else None
        if status not in STATUSES:
            return self.send_json({"error": "Estado inválido."}, HTTPStatus.BAD_REQUEST)
        with connection() as db:
            db.execute("UPDATE return_requests SET status = ? WHERE id = ?", (status, int(parts[2])))
            row = db.execute("SELECT * FROM return_requests WHERE id = ?", (int(parts[2]),)).fetchone()
        if row is None:
            return self.send_json({"error": "Solicitud no encontrada."}, HTTPStatus.NOT_FOUND)
        return self.send_json(dict(row))


if __name__ == "__main__":
    initialize_database()
    print("Mercado Viva disponible en http://localhost:8000")
    ThreadingHTTPServer(("", 8000), Handler).serve_forever()
