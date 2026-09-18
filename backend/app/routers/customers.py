from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Customer
from ..schemas import AudienceFilter, CustomerCreate, CustomerOut
from ..services.audience import resolve_audience

router = APIRouter(prefix="/api/customers", tags=["customers"])


@router.get("", response_model=list[CustomerOut])
def list_customers(
    db: Session = Depends(get_db),
    segment: str | None = None,
    limit: int = Query(100, le=500),
) -> list[Customer]:
    stmt = select(Customer).order_by(Customer.id).limit(limit)
    if segment:
        stmt = stmt.where(Customer.segment == segment)
    return list(db.scalars(stmt))


@router.post("", response_model=CustomerOut, status_code=201)
def create_customer(payload: CustomerCreate, db: Session = Depends(get_db)) -> Customer:
    if db.scalar(select(Customer).where(Customer.email == payload.email)):
        raise HTTPException(409, "Customer with this email already exists")
    customer = Customer(**payload.model_dump())
    db.add(customer)
    db.commit()
    return customer


@router.post("/preview-audience", response_model=list[CustomerOut])
def preview_audience(payload: AudienceFilter, db: Session = Depends(get_db)) -> list[Customer]:
    return resolve_audience(db, payload.model_dump())
