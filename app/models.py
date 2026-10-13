from typing import Optional
 
from pydantic import BaseModel, Field
 
 
class ProductIn(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    price: float = Field(ge=0)
    stock: int = Field(default=0, ge=0)
 
 
class ProductUpdate(BaseModel):
    # Every field is optional so the client can send only what changed.
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    price: Optional[float] = Field(default=None, ge=0)
    stock: Optional[int] = Field(default=None, ge=0)
 
 
class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    stock: int
 
 
class SaleIn(BaseModel):
    product_id: int
    quantity: int = Field(gt=0)
 
 
class SaleOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    total: float
    sold_at: str
 
 
 
class SaleOut(BaseModel):
    id: int
    product_id: int
    product_name: str
    quantity: int
    unit_price: float 
    total: float
    created_at: str