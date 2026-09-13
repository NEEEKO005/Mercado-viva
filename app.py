"""Backend Python de Mercado Viva. Ejecutar: python app.py"""
import hashlib
import json
import secrets
import sqlite3
from datetime import datetime
from email import policy
from email.parser import BytesParser
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

BASE_DIR = Path(__file__).resolve().parent
DATABASE = BASE_DIR / "mercado_viva.db"
UPLOADS = BASE_DIR / "uploads"
ALLOWED_CATEGORY = "technology"
STATUSES = {"Pendiente", "Aprobada", "Rechazada", "Procesada"}
SESSIONS = {}

def password(value): return hashlib.sha256(value.encode()).hexdigest()
def connection():
    db = sqlite3.connect(DATABASE); db.row_factory = sqlite3.Row; return db

def initialize_database():
    UPLOADS.mkdir(exist_ok=True)
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, role TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS employees (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL, position TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1);
        CREATE TABLE IF NOT EXISTS purchases (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, order_number TEXT NOT NULL, product TEXT NOT NULL, category TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS return_requests (id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT UNIQUE NOT NULL, order_number TEXT NOT NULL, email TEXT NOT NULL, product TEXT NOT NULL, category TEXT NOT NULL, reason TEXT NOT NULL, other_reason TEXT, photos TEXT DEFAULT '[]', status TEXT NOT NULL DEFAULT 'Pendiente', created_at TEXT NOT NULL);
        """)
        columns={row[1] for row in db.execute("PRAGMA table_info(return_requests)")}
        if "other_reason" not in columns: db.execute("ALTER TABLE return_requests ADD COLUMN other_reason TEXT")
        if "photos" not in columns: db.execute("ALTER TABLE return_requests ADD COLUMN photos TEXT DEFAULT '[]'")
        # Migra de forma segura los empleados que existían en la tabla antigua users.
        legacy_employees=db.execute("SELECT id,name,email,password_hash FROM users WHERE role='employee'").fetchall()
        for employee in legacy_employees:
            db.execute("""INSERT OR IGNORE INTO employees (id,name,email,password_hash,position,active)
                          VALUES (?,?,?,?,?,1)""",(employee["id"],employee["name"],employee["email"],employee["password_hash"],"Gestor de devoluciones"))
        db.execute("DELETE FROM users WHERE role='employee'")
        if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] == 0:
            db.executemany("INSERT INTO users (id,name,email,password_hash,role) VALUES (?,?,?,?,?)", [
              (1,"Camila Gómez","camila@email.com",password("Cliente2026!"),"customer")])
            db.executemany("INSERT INTO purchases (user_id,order_number,product,category) VALUES (?,?,?,?)", [
              (1,"MV-100842","Audífonos inalámbricos","Tecnología"),(1,"MV-100890","Teclado mecánico","Tecnología"),(1,"MV-100811","Cargador portátil","Tecnología")])
        if db.execute("SELECT COUNT(*) FROM employees").fetchone()[0] == 0:
            db.execute("""INSERT INTO employees (name,email,password_hash,position,active)
                          VALUES (?,?,?,?,1)""",("Operador Mercado Viva","empleado@mercadoviva.com",password("Empleado2026!"),"Gestor de devoluciones"))

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs): super().__init__(*args,directory=str(BASE_DIR),**kwargs)
    def send_json(self,data,status=HTTPStatus.OK):
        body=json.dumps(data,ensure_ascii=False).encode();self.send_response(status);self.send_header("Content-Type","application/json; charset=utf-8");self.send_header("Content-Length",str(len(body)));self.end_headers();self.wfile.write(body)
    def read_json(self):
        try:return json.loads(self.rfile.read(int(self.headers.get("Content-Length",0))).decode())
        except (ValueError,UnicodeDecodeError):return None
    def read_multipart(self):
        """Lee un formulario multipart/form-data sin usar el módulo cgi eliminado."""
        content_type=self.headers.get("Content-Type","")
        if "multipart/form-data" not in content_type:
            return None
        body=self.rfile.read(int(self.headers.get("Content-Length",0)))
        message=BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode()+body
        )
        fields,files={},[]
        for part in message.iter_parts():
            name=part.get_param("name",header="content-disposition")
            filename=part.get_filename()
            if filename:
                files.append({"filename":filename,"content_type":part.get_content_type(),"data":part.get_payload(decode=True)})
            elif name:
                fields[name]=part.get_content().strip()
        return fields,files
    def current_user(self, role=None):
        token=self.headers.get("Authorization","").removeprefix("Bearer "); user=SESSIONS.get(token)
        return user if user and (role is None or user["role"]==role) else None
    def do_GET(self):
        path=urlparse(self.path).path
        if path=="/api/purchases":
            user=self.current_user("customer")
            if not user:return self.send_json({"error":"Inicia sesión como cliente."},HTTPStatus.UNAUTHORIZED)
            with connection() as db: rows=db.execute("SELECT order_number,product,category FROM purchases WHERE user_id=? ORDER BY id DESC",(user["id"],)).fetchall()
            return self.send_json([dict(row) for row in rows])
        if path=="/api/returns":
            if not self.current_user("employee"):return self.send_json({"error":"Acceso exclusivo para empleados."},HTTPStatus.UNAUTHORIZED)
            with connection() as db: rows=db.execute("SELECT * FROM return_requests ORDER BY id DESC").fetchall()
            return self.send_json([dict(row) for row in rows])
        return super().do_GET()
    def do_POST(self):
        path=urlparse(self.path).path
        if path=="/api/login":
            data=self.read_json() or {}; role=data.get("role"); email=data.get("username","").strip().lower()
            table="employees" if role=="employee" else "users"
            query="SELECT * FROM employees WHERE email=? AND password_hash=? AND active=1" if role=="employee" else "SELECT * FROM users WHERE email=? AND role='customer' AND password_hash=?"
            with connection() as db:user=db.execute(query,(email,password(data.get("password","")))).fetchone()
            if not user:return self.send_json({"error":"Credenciales inválidas."},HTTPStatus.UNAUTHORIZED)
            token=secrets.token_urlsafe(32); SESSIONS[token]={"id":user["id"],"name":user["name"],"email":user["email"],"role":role}
            return self.send_json({"token":token,"name":user["name"],"email":user["email"],"role":role})
        if path!="/api/returns":return self.send_error(HTTPStatus.NOT_FOUND)
        # El inicio de sesión del cliente es opcional: solo agiliza la selección de compras.
        user=self.current_user("customer")
        parsed=self.read_multipart()
        if not parsed:return self.send_json({"error":"Formato de formulario inválido."},HTTPStatus.BAD_REQUEST)
        fields,uploaded=parsed
        get=lambda name: fields.get(name,"").strip()
        order,email,product,category,reason=map(get,("order_number","email","product","category","reason"))
        if not all((order,email,product,category,reason)):return self.send_json({"error":"Completa todos los campos obligatorios."},HTTPStatus.BAD_REQUEST)
        if user and email.lower()!=user["email"].lower():return self.send_json({"error":"El correo no corresponde a tu sesión."},HTTPStatus.FORBIDDEN)
        if category!=ALLOWED_CATEGORY:return self.send_json({"error":"Solo se aceptan devoluciones de productos tecnológicos."},HTTPStatus.UNPROCESSABLE_ENTITY)
        category="Tecnología"
        other=get("other_reason")
        if reason=="Otro" and not other:return self.send_json({"error":"Describe el otro motivo de devolución."},HTTPStatus.BAD_REQUEST)
        photos=[]
        for item in uploaded:
            if len(photos)>=3:return self.send_json({"error":"Máximo 3 fotos por solicitud."},HTTPStatus.BAD_REQUEST)
            if not item["content_type"].startswith("image/"):return self.send_json({"error":"Solo se permiten archivos de imagen."},HTTPStatus.BAD_REQUEST)
            extension=Path(item["filename"]).suffix.lower() or ".jpg"; filename=f"{secrets.token_hex(12)}{extension}"; (UPLOADS/filename).write_bytes(item["data"]);photos.append(f"uploads/{filename}")
        with connection() as db:
            cursor=db.execute("INSERT INTO return_requests (code,order_number,email,product,category,reason,other_reason,photos,status,created_at) VALUES ('TEMP',?,?,?,?,?,?,?,?,?)",(order,email,product,category,reason,other,json.dumps(photos),"Pendiente",datetime.now().isoformat(timespec="seconds")))
            code=f"DV-{cursor.lastrowid:05d}";db.execute("UPDATE return_requests SET code=? WHERE id=?",(code,cursor.lastrowid));row=db.execute("SELECT * FROM return_requests WHERE id=?",(cursor.lastrowid,)).fetchone()
        return self.send_json(dict(row),HTTPStatus.CREATED)
    def do_PATCH(self):
        parts=urlparse(self.path).path.strip("/").split("/")
        if len(parts)!=3 or parts[:2]!=["api","returns"] or not parts[2].isdigit():return self.send_error(HTTPStatus.NOT_FOUND)
        if not self.current_user("employee"):return self.send_json({"error":"Acceso exclusivo para empleados."},HTTPStatus.UNAUTHORIZED)
        data=self.read_json() or {};status=data.get("status")
        if status not in STATUSES:return self.send_json({"error":"Estado inválido."},HTTPStatus.BAD_REQUEST)
        with connection() as db:db.execute("UPDATE return_requests SET status=? WHERE id=?",(status,int(parts[2])));row=db.execute("SELECT * FROM return_requests WHERE id=?",(int(parts[2]),)).fetchone()
        return self.send_json(dict(row)) if row else self.send_json({"error":"Solicitud no encontrada."},HTTPStatus.NOT_FOUND)

if __name__=="__main__":
    initialize_database();print("Mercado Viva disponible en http://localhost:8000");ThreadingHTTPServer(("",8000),Handler).serve_forever()
