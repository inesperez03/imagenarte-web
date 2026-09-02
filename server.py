from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qs, quote, unquote, urlparse
from urllib.request import Request, urlopen
import cgi
import json
import mimetypes
import os
import shutil
import sqlite3
import uuid


BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("IMAGENARTE_DATA_DIR", BASE_DIR)).resolve()
DB_PATH = DATA_DIR / "imagenarte.db"
UPLOAD_DIR = DATA_DIR / "uploads"
ADMIN_PASSWORD = os.environ.get("IMAGENARTE_ADMIN_PASSWORD", "imagenarte")
HOST = os.environ.get("HOST", "localhost")
PORT = int(os.environ.get("PORT", "5173"))
SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "imagenes")
USE_SUPABASE = bool(SUPABASE_URL and SUPABASE_KEY)


SAMPLE_PRODUCTS = [
    {
        "title": "Mediterráneo Dorado",
        "type": "Paisaje",
        "colors": ["Azul", "Dorado", "Blanco"],
        "groups": ["Mediterráneo", "Clásico"],
        "size": "80 x 100 cm",
        "price": 420,
        "description": "Pieza luminosa con presencia decorativa para salón o despacho.",
        "available": True,
        "published": True,
        "createdAt": "2026-08-18T10:00:00.000Z",
    },
    {
        "title": "Composición Serena",
        "type": "Abstracto",
        "colors": ["Verde", "Negro", "Arena"],
        "groups": ["Moderno", "Texturas"],
        "size": "70 x 90 cm",
        "price": 360,
        "description": "Obra abstracta en tonos naturales con acabado elegante.",
        "available": True,
        "published": True,
        "createdAt": "2026-08-20T10:00:00.000Z",
    },
    {
        "title": "Lámina Botánica",
        "type": "Lámina",
        "colors": ["Verde", "Blanco", "Madera"],
        "groups": ["Botánico", "Enmarcado"],
        "size": "50 x 70 cm",
        "price": 145,
        "description": "Lámina decorativa con marco cálido y passepartout claro.",
        "available": True,
        "published": True,
        "createdAt": "2026-08-22T10:00:00.000Z",
    },
    {
        "title": "Rojo Interior",
        "type": "Óleo",
        "colors": ["Rojo", "Terracota", "Negro"],
        "groups": ["Contemporáneo", "Color"],
        "size": "90 x 90 cm",
        "price": 510,
        "description": "Óleo con contraste intenso para espacios con personalidad.",
        "available": True,
        "published": True,
        "createdAt": "2026-08-25T10:00:00.000Z",
    },
]


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    if USE_SUPABASE:
        return

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                type TEXT NOT NULL,
                colors TEXT NOT NULL,
                groups_json TEXT NOT NULL,
                size TEXT,
                price REAL,
                description TEXT,
                image TEXT,
                available INTEGER NOT NULL DEFAULT 1,
                published INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tags (
                id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(kind, name)
            )
            """
        )
        count = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
        if count == 0:
            for product in SAMPLE_PRODUCTS:
                conn.execute(
                    """
                    INSERT INTO products (
                        id, title, type, colors, groups_json, size, price,
                        description, image, available, published, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    product_values(str(uuid.uuid4()), product, "", product["createdAt"]),
                )
        seed_sqlite_tags(conn)


def product_from_row(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "type": row["type"],
        "colors": json.loads(row["colors"] or "[]"),
        "groups": json.loads(row["groups_json"] or "[]"),
        "size": row["size"] or "",
        "price": row["price"] if row["price"] is not None else "",
        "description": row["description"] or "",
        "image": row["image"] or "",
        "available": bool(row["available"]),
        "published": bool(row["published"]),
        "createdAt": row["created_at"],
        "updatedAt": row["updated_at"],
    }


def product_from_supabase(row):
    return {
        "id": row["id"],
        "title": row["title"],
        "type": row["type"],
        "colors": row.get("colors") or [],
        "groups": row.get("groups_json") or [],
        "size": row.get("size") or "",
        "price": row.get("price") if row.get("price") is not None else "",
        "description": row.get("description") or "",
        "image": row.get("image") or "",
        "available": bool(row.get("available")),
        "published": bool(row.get("published")),
        "createdAt": row.get("created_at"),
        "updatedAt": row.get("updated_at"),
    }


def list_from_value(value):
    if isinstance(value, list):
        return value
    return [item.strip() for item in (value or "").split(",") if item.strip()]


def normalize_tag_kind(kind):
    return kind if kind in ("types", "colors", "groups") else ""


def is_admin(handler):
    return handler.headers.get("X-Admin-Password", "") == ADMIN_PASSWORD


class ImagenarteHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/products":
            self.handle_list_products(parsed.query)
            return
        if parsed.path == "/api/tags":
            self.handle_list_tags()
            return
        self.serve_static(parsed.path)

    def do_POST(self):
        if self.path == "/api/products":
            self.require_admin_then(self.handle_create_product)
            return
        if self.path == "/api/tags":
            self.require_admin_then(self.handle_create_tag)
            return
        self.send_error(404)

    def do_PUT(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/products/"):
            product_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.require_admin_then(lambda: self.handle_update_product(product_id))
            return
        self.send_error(404)

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path.startswith("/api/products/"):
            product_id = unquote(parsed.path.rsplit("/", 1)[-1])
            self.require_admin_then(lambda: self.handle_delete_product(product_id))
            return
        self.send_error(404)

    def handle_list_products(self, query):
        if USE_SUPABASE:
            self.send_json({"products": supabase_list_products(query, is_admin(self))})
            return

        params = parse_qs(query)
        include_all = params.get("all", ["0"])[0] == "1" and is_admin(self)
        sql = "SELECT * FROM products"
        if not include_all:
            sql += " WHERE published = 1"
        sql += " ORDER BY datetime(created_at) DESC"

        with connect() as conn:
            products = [product_from_row(row) for row in conn.execute(sql)]
        self.send_json({"products": products})

    def handle_list_tags(self):
        if USE_SUPABASE:
            self.send_json({"tags": supabase_list_tags()})
            return

        tags = {"types": [], "colors": [], "groups": []}
        with connect() as conn:
            for row in conn.execute("SELECT kind, name FROM tags ORDER BY kind, name COLLATE NOCASE"):
                tags[row["kind"]].append(row["name"])
        self.send_json({"tags": tags})

    def handle_create_tag(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length).decode("utf-8")
        payload = json.loads(body or "{}")
        kind = normalize_tag_kind(payload.get("kind", ""))
        name = (payload.get("name", "") or "").strip()
        if not kind or not name:
            self.send_json({"error": "Etiqueta no valida"}, status=400)
            return

        if USE_SUPABASE:
            supabase_add_tag(kind, name)
            self.send_json({"tags": supabase_list_tags()})
            return

        with connect() as conn:
            add_sqlite_tag(conn, kind, name)
        self.handle_list_tags()

    def handle_create_product(self):
        fields, image_path = self.parse_form()
        product_id = str(uuid.uuid4())

        if USE_SUPABASE:
            product = supabase_create_product(product_id, fields, image_path)
            self.send_json({"product": product}, status=201)
            return

        with connect() as conn:
            ensure_sqlite_product_tags(conn, fields)
            conn.execute(
                """
                INSERT INTO products (
                    id, title, type, colors, groups_json, size, price,
                    description, image, available, published, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                product_values(product_id, fields, image_path, current_timestamp()),
            )
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        self.send_json({"product": product_from_row(row)}, status=201)

    def handle_update_product(self, product_id):
        if USE_SUPABASE:
            existing = supabase_get_product(product_id)
            if not existing:
                self.send_error(404)
                return
            fields, image_path = self.parse_form()
            final_image = image_path or existing.get("image") or ""
            product = supabase_update_product(product_id, fields, final_image)
            if image_path and existing.get("image"):
                delete_upload(existing["image"])
            self.send_json({"product": product})
            return

        with connect() as conn:
            existing = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if not existing:
                self.send_error(404)
                return

            fields, image_path = self.parse_form()
            ensure_sqlite_product_tags(conn, fields)
            final_image = image_path or existing["image"] or ""
            conn.execute(
                """
                UPDATE products
                SET title = ?, type = ?, colors = ?, groups_json = ?, size = ?,
                    price = ?, description = ?, image = ?, available = ?,
                    published = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                product_values_for_update(product_id, fields, final_image),
            )
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()

        if image_path and existing["image"]:
            delete_upload(existing["image"])
        self.send_json({"product": product_from_row(row)})

    def handle_delete_product(self, product_id):
        if USE_SUPABASE:
            existing = supabase_get_product(product_id)
            if not existing:
                self.send_error(404)
                return
            supabase_delete_product(product_id)
            if existing.get("image"):
                delete_upload(existing["image"])
            self.send_json({"ok": True})
            return

        with connect() as conn:
            existing = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
            if not existing:
                self.send_error(404)
                return
            conn.execute("DELETE FROM products WHERE id = ?", (product_id,))

        if existing["image"]:
            delete_upload(existing["image"])
        self.send_json({"ok": True})

    def parse_form(self):
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={
                "REQUEST_METHOD": self.command,
                "CONTENT_TYPE": self.headers.get("Content-Type", ""),
            },
        )
        fields = {}
        image_path = ""
        for key in form.keys():
            item = form[key]
            if key == "image" and getattr(item, "filename", ""):
                image_path = save_upload(item)
            elif not getattr(item, "filename", ""):
                fields[key] = item.value
        return fields, image_path

    def require_admin_then(self, callback):
        if not is_admin(self):
            self.send_json({"error": "No autorizado"}, status=401)
            return
        callback()

    def serve_static(self, request_path):
        relative = "index.html" if request_path in ("", "/") else request_path.lstrip("/")
        target = (BASE_DIR / relative).resolve()
        if not str(target).startswith(str(BASE_DIR)) or not target.is_file():
            self.send_error(404)
            return

        content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        with target.open("rb") as file:
            shutil.copyfileobj(file, self.wfile)

    def send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))


def product_values(product_id, fields, image_path, created_at):
    return (
        product_id,
        fields.get("title", "").strip(),
        fields.get("type", "").strip(),
        json.dumps(list_from_value(fields.get("colors", "")), ensure_ascii=False),
        json.dumps(list_from_value(fields.get("groups", "")), ensure_ascii=False),
        fields.get("size", "").strip(),
        parse_price(fields.get("price", "")),
        fields.get("description", "").strip(),
        image_path,
        parse_bool(fields.get("available", True)),
        parse_bool(fields.get("published", True)),
        created_at,
    )


def product_values_for_update(product_id, fields, image_path):
    values = product_values(product_id, fields, image_path, current_timestamp())
    return values[1:11] + (product_id,)


def product_payload(product_id, fields, image_path, created_at=None):
    payload = {
        "id": product_id,
        "title": fields.get("title", "").strip(),
        "type": fields.get("type", "").strip(),
        "colors": list_from_value(fields.get("colors", "")),
        "groups_json": list_from_value(fields.get("groups", "")),
        "size": fields.get("size", "").strip(),
        "price": parse_price(fields.get("price", "")),
        "description": fields.get("description", "").strip(),
        "image": image_path,
        "available": bool(parse_bool(fields.get("available", True))),
        "published": bool(parse_bool(fields.get("published", True))),
    }
    if created_at:
        payload["created_at"] = created_at
    return payload


def seed_sqlite_tags(conn):
    defaults = {"types": set(), "colors": set(), "groups": set()}
    for product in SAMPLE_PRODUCTS:
        defaults["types"].add(product["type"])
        defaults["colors"].update(product["colors"])
        defaults["groups"].update(product["groups"])
    for row in conn.execute("SELECT type, colors, groups_json FROM products"):
        defaults["types"].add(row["type"])
        defaults["colors"].update(json.loads(row["colors"] or "[]"))
        defaults["groups"].update(json.loads(row["groups_json"] or "[]"))
    for kind, names in defaults.items():
        for name in names:
            add_sqlite_tag(conn, kind, name)


def add_sqlite_tag(conn, kind, name):
    clean_kind = normalize_tag_kind(kind)
    clean_name = (name or "").strip()
    if clean_kind and clean_name:
        conn.execute(
            "INSERT OR IGNORE INTO tags (id, kind, name) VALUES (?, ?, ?)",
            (str(uuid.uuid4()), clean_kind, clean_name),
        )


def ensure_sqlite_product_tags(conn, fields):
    add_sqlite_tag(conn, "types", fields.get("type", ""))
    for color in list_from_value(fields.get("colors", "")):
        add_sqlite_tag(conn, "colors", color)
    for group in list_from_value(fields.get("groups", "")):
        add_sqlite_tag(conn, "groups", group)


def supabase_headers(extra=None):
    headers = {"apikey": SUPABASE_KEY, "Authorization": f"Bearer {SUPABASE_KEY}"}
    if extra:
        headers.update(extra)
    return headers


def supabase_request(method, path, body=None, headers=None):
    data = None
    final_headers = supabase_headers(headers)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
        final_headers["Content-Type"] = "application/json"

    request = Request(f"{SUPABASE_URL}{path}", data=data, headers=final_headers, method=method)
    try:
        with urlopen(request, timeout=20) as response:
            raw = response.read()
            return json.loads(raw.decode("utf-8")) if raw else None
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase error {error.code}: {detail}") from error


def supabase_list_products(query, admin):
    params = parse_qs(query)
    include_all = params.get("all", ["0"])[0] == "1" and admin
    path = "/rest/v1/products?select=*&order=created_at.desc"
    if not include_all:
        path += "&published=eq.true"
    return [product_from_supabase(row) for row in supabase_request("GET", path)]


def supabase_get_product(product_id):
    rows = supabase_request("GET", f"/rest/v1/products?id=eq.{quote(product_id)}&select=*&limit=1")
    return product_from_supabase(rows[0]) if rows else None


def supabase_create_product(product_id, fields, image_path):
    ensure_supabase_product_tags(fields)
    rows = supabase_request(
        "POST",
        "/rest/v1/products",
        [product_payload(product_id, fields, image_path, current_timestamp())],
        {"Prefer": "return=representation"},
    )
    return product_from_supabase(rows[0])


def supabase_update_product(product_id, fields, image_path):
    ensure_supabase_product_tags(fields)
    payload = product_payload(product_id, fields, image_path)
    payload.pop("id", None)
    rows = supabase_request(
        "PATCH",
        f"/rest/v1/products?id=eq.{quote(product_id)}",
        payload,
        {"Prefer": "return=representation"},
    )
    return product_from_supabase(rows[0])


def supabase_delete_product(product_id):
    supabase_request("DELETE", f"/rest/v1/products?id=eq.{quote(product_id)}", headers={"Prefer": "return=minimal"})


def supabase_list_tags():
    tags = {"types": [], "colors": [], "groups": []}
    rows = supabase_request("GET", "/rest/v1/tags?select=kind,name&order=kind.asc,name.asc")
    for row in rows:
        if row["kind"] in tags:
            tags[row["kind"]].append(row["name"])
    if not any(tags.values()):
        for product in SAMPLE_PRODUCTS:
            supabase_add_tag("types", product["type"])
            for color in product["colors"]:
                supabase_add_tag("colors", color)
            for group in product["groups"]:
                supabase_add_tag("groups", group)
        return supabase_list_tags()
    return tags


def supabase_add_tag(kind, name):
    clean_kind = normalize_tag_kind(kind)
    clean_name = (name or "").strip()
    if not clean_kind or not clean_name:
        return
    supabase_request(
        "POST",
        "/rest/v1/tags?on_conflict=kind,name",
        [{"id": str(uuid.uuid4()), "kind": clean_kind, "name": clean_name}],
        {"Prefer": "resolution=ignore-duplicates"},
    )


def ensure_supabase_product_tags(fields):
    supabase_add_tag("types", fields.get("type", ""))
    for color in list_from_value(fields.get("colors", "")):
        supabase_add_tag("colors", color)
    for group in list_from_value(fields.get("groups", "")):
        supabase_add_tag("groups", group)


def parse_price(value):
    if value in ("", None):
        return None
    try:
        return float(value)
    except ValueError:
        return None


def parse_bool(value):
    return 1 if str(value).lower() in ("1", "true", "yes", "on") else 0


def save_upload(item):
    extension = Path(item.filename).suffix.lower()
    if extension not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        extension = ".jpg"
    filename = f"{uuid.uuid4()}{extension}"

    if USE_SUPABASE:
        return save_supabase_upload(item, filename)

    target = UPLOAD_DIR / filename
    with target.open("wb") as file:
        shutil.copyfileobj(item.file, file)
    return f"/uploads/{filename}"


def save_supabase_upload(item, filename):
    data = item.file.read()
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    encoded_name = quote(filename)
    request = Request(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}/{encoded_name}",
        data=data,
        headers=supabase_headers(
            {
                "Content-Type": content_type,
                "x-upsert": "true",
            }
        ),
        method="POST",
    )
    try:
        with urlopen(request, timeout=30):
            pass
    except HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase storage error {error.code}: {detail}") from error
    return f"{SUPABASE_URL}/storage/v1/object/public/{SUPABASE_BUCKET}/{encoded_name}"


def delete_upload(image_path):
    if USE_SUPABASE and f"/storage/v1/object/public/{SUPABASE_BUCKET}/" in image_path:
        filename = image_path.rsplit("/", 1)[-1]
        delete_supabase_upload(filename)
        return

    if not image_path.startswith("/uploads/"):
        return
    target = (BASE_DIR / image_path.lstrip("/")).resolve()
    if str(target).startswith(str(UPLOAD_DIR.resolve())) and target.exists():
        target.unlink()


def delete_supabase_upload(filename):
    body = json.dumps({"prefixes": [unquote(filename)]}).encode("utf-8")
    request = Request(
        f"{SUPABASE_URL}/storage/v1/object/{SUPABASE_BUCKET}",
        data=body,
        headers=supabase_headers({"Content-Type": "application/json"}),
        method="DELETE",
    )
    try:
        with urlopen(request, timeout=20):
            pass
    except HTTPError:
        pass


def current_timestamp():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


if __name__ == "__main__":
    init_db()
    server = ThreadingHTTPServer((HOST, PORT), ImagenarteHandler)
    print(f"Imagenarte: http://{HOST}:{PORT}")
    server.serve_forever()
