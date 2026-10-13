from typing import List, Optional

from fastapi import FastAPI, Request, Response, status
from fastapi.responses import JSONResponse

from database import AppError, Database, ProductRepository, SaleService
from schemas import ProductIn, ProductOut, ProductUpdate, SaleIn, SaleOut

app = FastAPI(title="Easy Store", description="Simple product and sales system.")
db = Database("store.db")
products = ProductRepository(db)
sales = SaleService(db)


@app.exception_handler(AppError)
def handle_app_error(_request: Request, error: AppError):
    return JSONResponse(status_code=error.status_code, content={"detail": error.message})


@app.get("/")
def home():
    return {"message": "Easy Store is running.", "docs": "/docs"}


@app.post("/products", status_code=status.HTTP_201_CREATED, response_model=ProductOut)
def create_product(body: ProductIn):
    return products.create(body.name, body.price, body.stock)


@app.get("/products", response_model=List[ProductOut])
def list_products(search: Optional[str] = None):
    return products.list(search)


@app.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int):
    return products.get(product_id)


# PATCH because we only update the fields the client sends.
@app.patch("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, body: ProductUpdate):
    return products.update(product_id, body.model_dump(exclude_unset=True))


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int):
    products.delete(product_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post("/sales", status_code=status.HTTP_201_CREATED, response_model=SaleOut)
def make_sale(body: SaleIn):
    return sales.sell(body.product_id, body.quantity)


@app.get("/sales", response_model=List[SaleOut])
def list_sales():
    return sales.list()


@app.get("/sales/revenue")
def revenue():
    return {"total_revenue": sales.total_revenue()}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)