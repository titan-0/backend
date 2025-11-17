from fastapi import FastAPI, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db, engine, Base
from models import Order, BrokerConfig

app = FastAPI(title="Positions Readonly API")

# CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "positions-api",
        "endpoints": ["/health", "/positions_json", "/aliases"],
        "pagination": {"params": ["page", "limit"], "defaults": {"page": 1, "limit": 20}},
        "filters": ["broker", "client_id", "ticker", "product", "action", "account"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/positions_json")
async def positions_json(
    broker: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    account: Optional[str] = Query(None),

    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=20),

    db: AsyncSession = Depends(get_db)
):
    conditions = [(Order.quantity_filled - Order.quantity_exited != 0)]
    if broker:
        conditions.append(Order.broker == broker)
    if client_id:
        conditions.append(Order.client_id == client_id)
    if ticker:
        conditions.append(Order.ticker == ticker)
    if product:
        conditions.append(Order.product == product)
    if action:
        conditions.append(Order.action == action)
    if account:
        conditions.append(Order.brokeraccount == account)

    offset = (page - 1) * limit

    query = (
        select(Order)
        .where(*conditions)
        .order_by(Order.order_id)
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    def to_float(v):
        if v is None: return None
        try: return float(v)
        except: return None

    def to_date_str(d):
        if d is None: return None
        try: return d.isoformat()
        except: return None

    out = []
    for p in rows:
        out.append({
            "order_id": int(p.order_id) if p.order_id else None,
            "ticker": p.ticker,
            "client_id": p.client_id,
            "broker": p.broker,
            "brokeraccount": p.brokeraccount,
            "product": p.product,
            "action": p.action,
            "quantity": int(p.quantity) if p.quantity else 0,
            "price": to_float(p.price),
            "stoploss_price": to_float(p.stoploss_price),
            "takeprofit_price": to_float(p.takeprofit_price),
            "equity": to_float(p.equity),
            "quantity_filled": int(p.quantity_filled) if p.quantity_filled else 0,
            "quantity_exited": int(p.quantity_exited) if p.quantity_exited else 0,
            "date_entrylast": to_date_str(p.date_entrylast),
            "date_exit": to_date_str(p.date_exit),
        })

    return out


@app.get("/aliases")
async def aliases(db: AsyncSession = Depends(get_db)):
    # Return list of alias strings directly from DB
    result = await db.execute(select(BrokerConfig.alias))
    return [row[0] for row in result.all()]
