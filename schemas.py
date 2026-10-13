from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

SQLITE_MAX_INT = 2**63 - 1  # larger ints make sqlite3 raise OverflowError (a 500 error)


class ProductIn(BaseModel):
    """Data needed to create a product."""
    model_config = ConfigDict(str_strip_whitespace=True)  # "   " becomes "" and is rejected

    name: str = Field(min_length=1)
    price: float = Field(ge=0, allow_inf_nan=False)
    stock: int = Field(ge=0, le=SQLITE_MAX_INT)


class ProductUpdate(BaseModel):
    """Every field is optional, so you can change just one."""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1)
    price: Optional[float] = Field(default=None, ge=0, allow_inf_nan=False)
    stock: Optional[int] = Field(default=None, ge=0, le=SQLITE_MAX_INT)


class ProductOut(BaseModel):
    """What the API returns for a product."""
    id: int
    name: str
    price: float
    stock: int


class SaleIn(BaseModel):
    """Data needed to record a sale."""
    product_id: int = Field(le=SQLITE_MAX_INT)
    quantity: int = Field(gt=0, le=SQLITE_MAX_INT)


class SaleOut(BaseModel):
    """What the API returns for a sale."""
    id: int
    product_id: int
    product_name: str
    quantity: int
    total: float
    sold_at: str