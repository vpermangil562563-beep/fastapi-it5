# Easy Store

A simple FastAPI + SQLite API for managing products and recording sales. Selling a product checks the stock, reduces it, and saves the sale in one transaction, and the API can report the total revenue.

## Setup (Windows, PowerShell)

```powershell
git clone <your-repo-url>
cd <your-project-folder>
```

With venv and pip:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

With uv:

```powershell
uv venv
.\.venv\Scripts\Activate.ps1
uv pip install -r requirements.txt
```

If there is no `requirements.txt`, install the two packages directly:

```powershell
python -m pip install fastapi uvicorn
```

If PowerShell blocks the activate script, run this once in the same window and activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## Run

Run these from the project folder (the one that contains `main.py`):

```powershell
uvicorn main:app --reload
```

You can also start it with:

```powershell
python main.py
```

Open http://127.0.0.1:8000/docs to try every endpoint (click an endpoint, then Try it out). The database file `store.db` is created in the project folder on first start. To start from an empty database, stop the server and delete `store.db`.

## Project tree

```text
main.py            Routes and the error handler
database.py        Database, ProductRepository, SaleService, AppError
schemas.py         Pydantic models
requirements.txt
store.db           Created automatically
```

## Sample tests

Run them in order on an empty database, using the /docs page. Each step shows the request, the body to send (JSON), and the output to expect (JSON).

- `sold_at` is the date and time of the sale in the form `YYYY-MM-DD HH:MM:SS`, so yours will differ.
- Errors come back as `{"detail": "<message>"}`.
- Input mistakes come back as `{"detail": [ ... ]}` with a `loc` naming the bad field.

### Root

**1. Welcome message**

```http
GET /
```

Expect:

```json
{
  "message": "Easy Store is running.",
  "docs": "/docs"
}
```

### Products

**2. Add a product**

```http
POST /products
```

Body:

```json
{
  "name": "Notebook",
  "price": 45.5,
  "stock": 20
}
```

Expect:

```json
{
  "id": 1,
  "name": "Notebook",
  "price": 45.5,
  "stock": 20
}
```

**3. Add two more products**

```http
POST /products
```

Send each body one at a time. They return ids 2 and 3.

```json
{
  "name": "Ballpen",
  "price": 12,
  "stock": 50
}
```

```json
{
  "name": "Backpack",
  "price": 650,
  "stock": 3
}
```

**4. Duplicate name**

```http
POST /products
```

Body:

```json
{
  "name": "Notebook",
  "price": 10,
  "stock": 1
}
```

Expect:

```json
{
  "detail": "A product with that name already exists."
}
```

**5. Invalid input**

```http
POST /products
```

Body:

```json
{
  "name": "Eraser",
  "price": -5,
  "stock": 10
}
```

Expect (the exact wording can differ slightly between Pydantic versions):

```json
{
  "detail": [
    {
      "type": "greater_than_equal",
      "loc": ["body", "price"],
      "msg": "Input should be greater than or equal to 0",
      "input": -5,
      "ctx": { "ge": 0 }
    }
  ]
}
```

An empty name, a negative stock, or a missing field gives the same kind of error.

**6. List all products**

```http
GET /products
```

Expect: the 3 products ordered by name.

```json
[
  { "id": 3, "name": "Backpack", "price": 650.0, "stock": 3 },
  { "id": 2, "name": "Ballpen", "price": 12.0, "stock": 50 },
  { "id": 1, "name": "Notebook", "price": 45.5, "stock": 20 }
]
```

**7. Search by name**

```http
GET /products?search=note
```

Expect:

```json
[
  { "id": 1, "name": "Notebook", "price": 45.5, "stock": 20 }
]
```

The search matches part of the name and ignores letter case. `GET /products?search=ball` returns only Ballpen, and `GET /products?search=NOTE` returns only Notebook.

**8. Get one product**

```http
GET /products/1
```

Expect:

```json
{
  "id": 1,
  "name": "Notebook",
  "price": 45.5,
  "stock": 20
}
```

```http
GET /products/99
```

Expect:

```json
{
  "detail": "Product not found."
}
```

**9. Update a product (only the fields you send)**

```http
PATCH /products/1
```

Body:

```json
{
  "price": 50
}
```

Expect (name and stock are unchanged):

```json
{
  "id": 1,
  "name": "Notebook",
  "price": 50.0,
  "stock": 20
}
```

**10. Update errors**

```http
PATCH /products/1
```

Body (name already used by another product):

```json
{
  "name": "Ballpen"
}
```

Expect:

```json
{
  "detail": "A product with that name already exists."
}
```

```http
PATCH /products/99
```

Body:

```json
{
  "price": 1
}
```

Expect:

```json
{
  "detail": "Product not found."
}
```

### Sales

**11. Record a sale**

```http
POST /sales
```

Body:

```json
{
  "product_id": 1,
  "quantity": 2
}
```

Expect (total is price 50.0 times quantity 2):

```json
{
  "id": 1,
  "product_id": 1,
  "product_name": "Notebook",
  "quantity": 2,
  "total": 100.0,
  "sold_at": "YYYY-MM-DD HH:MM:SS"
}
```

`GET /products/1` now shows `"stock": 18`.

**12. Not enough stock (nothing is saved)**

```http
POST /sales
```

Body:

```json
{
  "product_id": 3,
  "quantity": 5
}
```

Expect:

```json
{
  "detail": "Not enough stock. Only 3 left."
}
```

`GET /products/3` still shows `"stock": 3`, and `GET /sales` still lists only sale 1. The failed sale changed nothing.

**13. Unknown product and bad quantity**

```http
POST /sales
```

Body:

```json
{
  "product_id": 99,
  "quantity": 1
}
```

Expect:

```json
{
  "detail": "Product not found."
}
```

A `"quantity": 0` gives an input error naming `quantity`.

**14. Sell the last items**

```http
POST /sales
```

Body:

```json
{
  "product_id": 3,
  "quantity": 3
}
```

Expect (3 times 650.0):

```json
{
  "id": 2,
  "product_id": 3,
  "product_name": "Backpack",
  "quantity": 3,
  "total": 1950.0,
  "sold_at": "YYYY-MM-DD HH:MM:SS"
}
```

`GET /products/3` now shows `"stock": 0`. Sending the same sale again expects:

```json
{
  "detail": "Not enough stock. Only 0 left."
}
```

**15. List sales (newest first)**

```http
GET /sales
```

Expect:

```json
[
  {
    "id": 2,
    "product_id": 3,
    "product_name": "Backpack",
    "quantity": 3,
    "total": 1950.0,
    "sold_at": "YYYY-MM-DD HH:MM:SS"
  },
  {
    "id": 1,
    "product_id": 1,
    "product_name": "Notebook",
    "quantity": 2,
    "total": 100.0,
    "sold_at": "YYYY-MM-DD HH:MM:SS"
  }
]
```

**16. Total revenue**

```http
GET /sales/revenue
```

Expect (100.0 plus 1950.0):

```json
{
  "total_revenue": 2050.0
}
```

### Deleting products

**17. Delete a product with no sales**

```http
DELETE /products/2
```

Expect: an empty response (deleted). Repeating it expects:

```json
{
  "detail": "Product not found."
}
```

**18. Delete a product that has sales**

```http
DELETE /products/1
```

Expect:

```json
{
  "detail": "This product has sales records and cannot be deleted."
}
```

`GET /products` now lists only Backpack and Notebook.