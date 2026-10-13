import sqlite3
from contextlib import contextmanager
from typing import Dict, List, Optional
 
 
class AppError(Exception):
    """An error we raise on purpose; main.py turns it into an HTTP response."""
 
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
 
 
class Database:
    """Opens connections and creates the tables."""
 
    def __init__(self, path: str = "store.db"):
        self.path = path
        self.create_tables()
 
    @contextmanager
    def session(self):
        """Commit if everything worked, roll back everything if anything fails."""
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
 
    def create_tables(self):
        with self.session() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS products (
                    id    INTEGER PRIMARY KEY AUTOINCREMENT,
                    name  TEXT    NOT NULL UNIQUE,
                    price REAL    NOT NULL CHECK (price >= 0),
                    stock INTEGER NOT NULL CHECK (stock >= 0)
                );
                CREATE TABLE IF NOT EXISTS sales (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    quantity   INTEGER NOT NULL CHECK (quantity > 0),
                    total      REAL    NOT NULL,
                    sold_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products (id)
                );
            """)
 
 
def _product_integrity_error(e: sqlite3.IntegrityError) -> AppError:
    """Turn a SQLite IntegrityError into the right AppError."""
    msg = str(e)
    if "UNIQUE" in msg:
        return AppError("A product with that name already exists.", 409)
    if "CHECK" in msg or "NOT NULL" in msg:
        return AppError("Invalid data: price and stock must be 0 or more, and no field can be empty.", 400)
    if "FOREIGN KEY" in msg:
        return AppError("This product has sales records and cannot be deleted.", 409)
    return AppError("Database constraint failed.", 400)
 
 
class ProductRepository:
    """Create, Read, Update, Delete for products."""
 
    def __init__(self, db: Database):
        self.db = db
 
    def create(self, name: str, price: float, stock: int) -> Dict:
        try:
            with self.db.session() as conn:
                cur = conn.execute(
                    "INSERT INTO products (name, price, stock) VALUES (?, ?, ?)",
                    (name, price, stock))
                new_id = cur.lastrowid
        except sqlite3.IntegrityError as e:
            raise _product_integrity_error(e)
        return self.get(new_id)
 
    def get(self, product_id: int) -> Dict:
        with self.db.session() as conn:
            row = conn.execute("SELECT * FROM products WHERE id = ?", (product_id,)).fetchone()
        if row is None:
            raise AppError("Product not found.", 404)
        return dict(row)
 
    def list(self, search: Optional[str] = None) -> List[Dict]:
        with self.db.session() as conn:
            if search:
                escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("", "\\")
                rows = conn.execute(
                    "SELECT * FROM products WHERE name LIKE ? ESCAPE '\\' ORDER BY name",
                    (f"%{escaped}%",))
            else:
                rows = conn.execute("SELECT * FROM products ORDER BY name")
            return [dict(r) for r in rows]
 
    def update(self, product_id: int, changes: Dict) -> Dict:
        self.get(product_id)  # raises 404 if it does not exist
        allowed = {k: v for k, v in changes.items()
                   if k in ("name", "price", "stock") and v is not None}
        if allowed:
            columns = ", ".join(f"{k} = ?" for k in allowed)
            try:
                with self.db.session() as conn:
                    conn.execute(f"UPDATE products SET {columns} WHERE id = ?",
                                 (*allowed.values(), product_id))
            except sqlite3.IntegrityError as e:
                raise _product_integrity_error(e)
        return self.get(product_id)
 
    def delete(self, product_id: int) -> None:
        self.get(product_id)
        try:
            with self.db.session() as conn:
                conn.execute("DELETE FROM products WHERE id = ?", (product_id,))
        except sqlite3.IntegrityError as e:
            raise _product_integrity_error(e)
 
 
class SaleService:
    """The transaction: selling a product changes two tables at once."""
 
    def __init__(self, db: Database):
        self.db = db
 
    def sell(self, product_id: int, quantity: int) -> Dict:
        if quantity <= 0:
            raise AppError("Quantity must be at least 1.", 400)
 
        with self.db.session() as conn:
            cur = conn.execute(
                "UPDATE products SET stock = stock - ? WHERE id = ? AND stock >= ?",
                (quantity, product_id, quantity))
 
            if cur.rowcount == 0:
                product = conn.execute(
                    "SELECT stock FROM products WHERE id = ?", (product_id,)).fetchone()
                if product is None:
                    raise AppError("Product not found.", 404)
                raise AppError(f"Not enough stock. Only {product['stock']} left.", 409)
 
            price = conn.execute(
                "SELECT price FROM products WHERE id = ?", (product_id,)).fetchone()["price"]
            total = round(price * quantity, 2)
 
            cur = conn.execute(
                "INSERT INTO sales (product_id, quantity, total) VALUES (?, ?, ?)",
                (product_id, quantity, total))
            sale_id = cur.lastrowid
        return self.get(sale_id)
 
    def get(self, sale_id: int) -> Dict:
        with self.db.session() as conn:
            row = conn.execute("""
                SELECT s.id, s.product_id, p.name AS product_name,
                       s.quantity, s.total, s.sold_at
                FROM sales s JOIN products p ON p.id = s.product_id
                WHERE s.id = ?""", (sale_id,)).fetchone()
        if row is None:
            raise AppError("Sale not found.", 404)
        return dict(row)
 
    def list(self) -> List[Dict]:
        with self.db.session() as conn:
            rows = conn.execute("""
                SELECT s.id, s.product_id, p.name AS product_name,
                       s.quantity, s.total, s.sold_at
                FROM sales s JOIN products p ON p.id = s.product_id
                ORDER BY s.id DESC""")
            return [dict(r) for r in rows]
 
    def total_revenue(self) -> float:
        with self.db.session() as conn:
            total = conn.execute("SELECT COALESCE(SUM(total), 0) FROM sales").fetchone()[0]
        return round(total, 2)