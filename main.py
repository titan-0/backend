from fastapi import FastAPI, Depends, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
from pydantic import BaseModel
from datetime import datetime, date

from database import get_db, engine, Base
from models import Order, BrokerConfig,InternalOrder,BrokerOrder,Trade
from auth import LoginRequest, TokenResponse, create_access_token, verify_token

app = FastAPI(title="Positions Readonly API")

# CORS for local frontend dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins
    allow_credentials=False,  # Must be False when using "*"
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "positions-api",
        "endpoints": ["/health", "/positions_json", "/aliases","/internal_order","/broker_order","/trades","/login"],
        "pagination": {"params": ["page", "limit"], "defaults": {"page": 1, "limit": 20}},
        "filters": ["broker", "client_id", "ticker", "product", "action", "account"],
    }


@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/login")
async def login(credentials: LoginRequest):
    """
    Simple login endpoint for testing.
    In production, validate against a real user database.
    """
    # For demo purposes, accept any email and password
    # In production, validate against actual credentials in database
    email = credentials.email
    
    # Create JWT token
    token = create_access_token(email)
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user={"email": email}
    )

@app.on_event("startup")
async def startup():
    try:
        print("Starting database initialization...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database tables created successfully")
    except Exception as e:
        print(f"✗ Error creating tables: {e}")
        import traceback
        traceback.print_exc()


@app.get("/positions_json")
async def positions_json(
    broker: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    open_only: bool = Query(False, description="Show only open positions"),

    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),

    db: AsyncSession = Depends(get_db)
):
    conditions = []
    if open_only:
        conditions.append(Order.quantity_filled - Order.quantity_exited != 0)
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

    # Count total records
    count_query = select(func.count()).select_from(Order).where(*conditions) if conditions else select(func.count()).select_from(Order)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch paginated data
    offset = (page - 1) * limit
    query_builder = select(Order)
    if conditions:
        query_builder = query_builder.where(*conditions)
    
    query = (
        query_builder
        .order_by(Order.order_id.desc())
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



@app.get("/internal_order")
async def internal_order(
    strategy_id: Optional[str] = Query(None),
    order_id: Optional[str] = Query(None),
    broker: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    product: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    open_only: bool = Query(False),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    
    # Build conditions
    conditions = []
    if open_only:
        conditions.append(InternalOrder.quantity_filled - InternalOrder.quantity_exited != 0)
    
    if strategy_id:
        conditions.append(InternalOrder.strategy_id.ilike(f"%{strategy_id}%"))
    if order_id:
        try:
            conditions.append(InternalOrder.order_id == int(order_id))
        except (ValueError, TypeError):
            pass  # Skip if order_id is not a valid integer
    if broker:
        conditions.append(InternalOrder.broker == broker)
    if client_id:
        conditions.append(InternalOrder.client_id == client_id)
    if ticker:
        conditions.append(InternalOrder.ticker == ticker)
    if product:
        conditions.append(InternalOrder.product == product)
    if action:
        conditions.append(InternalOrder.action == action)
    if account:
        conditions.append(InternalOrder.brokeraccount == int(account))

    # Count total records
    count_query = select(func.count()).select_from(InternalOrder).where(*conditions) if conditions else select(func.count()).select_from(InternalOrder)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch paginated data
    offset = (page - 1) * limit
    query_builder = select(InternalOrder)
    if conditions:
        query_builder = query_builder.where(*conditions)
    
    query = (
        query_builder
        .order_by(InternalOrder.last_updated.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    def to_float(v):
        return float(v) if v is not None else None

    def to_datetime_str(d):
        return d.isoformat() if d is not None else None

    out = []
    for p in rows:
        out.append({
            "strategy_id": p.strategy_id,
            "order_id": int(p.order_id),
            "client_id": p.client_id,
            "ticker": p.ticker,
            "product": p.product,
            "quantity": int(p.quantity) if p.quantity else 0,
            "price": to_float(p.price),
            "trigger_price": to_float(p.trigger_price),
            "takeprofit_price": to_float(p.takeprofit_price),
            "stoploss_price": to_float(p.stoploss_price),
            "action": p.action,
            "last_updated": to_datetime_str(p.last_updated_date),
            "quantity_filled": int(p.quantity_filled) if p.quantity_filled else 0,
            "quantity_exited": int(p.quantity_exited) if p.quantity_exited else 0,
            "entry_status": p.entry_status,
            "exit_status": p.exit_status,
            "remarks": p.remarks,
            "ordertime": to_datetime_str(p.ordertime),
            "lotsize": int(p.lotsize) if p.lotsize else None,
            "equity": to_float(p.equity),
            "signal": int(p.signal_id) if p.signal_id else None
        })

    return {
        "data": out,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/broker_order")
async def broker_order(
    id: Optional[int] = Query(None),
    order_id: Optional[str] = Query(None),
    broker: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
    
    conditions = []
    
    if id:
        conditions.append(BrokerOrder.id == id)
    if order_id:
        conditions.append(BrokerOrder.order_id.ilike(f"%{order_id}%"))
    if broker:
        conditions.append(BrokerOrder.broker == broker)
    if client_id:
        conditions.append(BrokerOrder.client_id == client_id)
    if ticker:
        conditions.append(BrokerOrder.tradingsymbol.ilike(f"%{ticker}%"))
    if status:
        conditions.append(BrokerOrder.status == status)
    if account:
        conditions.append(BrokerOrder.brokeraccount == int(account))

    # Count total records
    count_query = select(func.count()).select_from(BrokerOrder).where(*conditions) if conditions else select(func.count()).select_from(BrokerOrder)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch paginated data
    offset = (page - 1) * limit
    query_builder = select(BrokerOrder)
    if conditions:
        query_builder = query_builder.where(*conditions)
    
    query = (
        query_builder
        .order_by(BrokerOrder.exchange_timestamp.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    def to_float(v):
        return float(v) if v is not None else None

    def to_datetime_str(d):
        return d.isoformat() if d is not None else None

    out = []
    for p in rows:
        out.append({
            "id": p.id,
            "order_id": p.order_id,
            "client_id": p.client_id,
            "tradingsymbol": p.tradingsymbol,
            "order_timestamp": to_datetime_str(p.order_timestamp),
            "exchange": p.exchange,
            "order_type": p.order_type,
            "quantity": int(p.quantity) if p.quantity else 0,
            "price": to_float(p.price),
            "trigger_price": to_float(p.trigger_price),
            "product": p.product,
            "broker": p.broker,
            "brokeraccount": p.brokeraccount,
            "status": p.status,
            "filled_quantity": int(p.filled_quantity) if p.filled_quantity else 0,
            "average_price": to_float(p.average_price),
            "status_message": p.status_message,
            "exchange_timestamp":to_datetime_str(p.exchange_timestamp)
        })

    return {
        "data": out,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }


@app.get("/trades")
async def trades(
    trade_id: Optional[int] = Query(None),
    broker: Optional[str] = Query(None),
    client_id: Optional[str] = Query(None),
    ticker: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    account: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db)
):
   
    
    conditions = []
    
    if trade_id:
        conditions.append(Trade.id == trade_id)
    if broker:
        conditions.append(Trade.broker == broker)
    if client_id:
        conditions.append(Trade.client_id == client_id)
    if ticker:
        conditions.append(Trade.ticker.ilike(f"%{ticker}%"))
    if action:
        conditions.append(Trade.action == action)
    if account:
        conditions.append(Trade.brokeraccount == int(account))

    # Count total records
    count_query = select(func.count()).select_from(Trade).where(*conditions) if conditions else select(func.count()).select_from(Trade)
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Fetch paginated data
    offset = (page - 1) * limit
    query_builder = select(Trade)
    if conditions:
        query_builder = query_builder.where(*conditions)
    
    query = (
        query_builder
        .order_by(Trade.exchange_timestamp.desc())
        .limit(limit)
        .offset(offset)
    )

    result = await db.execute(query)
    rows = result.scalars().all()

    def to_float(v):
        return float(v) if v is not None else None

    def to_datetime_str(d):
        return d.isoformat() if d is not None else None

    out = []
    for p in rows:
        total_charges = sum([
            to_float(p.brokerage_charge) or 0,
            to_float(p.exchange_charge) or 0,
            to_float(p.gst_charge) or 0,
            to_float(p.stt_charge) or 0,
            to_float(p.stampduty_charge) or 0,
            to_float(p.sebi_charge) or 0,
            to_float(p.other_charge) or 0,
            to_float(p.clearing_charge) or 0,
            to_float(p.brokerage_fix_charge) or 0,
            to_float(p.fixed_charges_other) or 0,
        ])
        
        out.append({
            "trade_id": p.trade_primarykey_id,
            "ticker": p.ticker,
            "client_id": p.client_id,
            "broker": p.broker,
            "brokeraccount": p.brokeraccount,
            "product": p.product,
            "action": p.action,
            "quantity": int(p.quantity) if p.quantity else 0,
            "price": to_float(p.price),
            "exchange": p.exchange,
            "exchange_timestamp": to_datetime_str(p.exchange_timestamp),
            "exchange_order_id": int(p.exchange_order_id) if p.exchange_order_id else None,
            "broker_order_id": int(p.broker_order_id) if p.broker_order_id else None,
            "broker_trade_id": int(p.broker_trade_id) if p.broker_trade_id else None,
            "internalorder_id": int(p.internalorder_id) if p.internalorder_id else None,
        })

    return {
        "data": out,
        "pagination": {
            "page": page,
            "limit": limit,
            "total": total,
            "pages": (total + limit - 1) // limit
        }
    }




@app.get("/aliases")
async def aliases(db: AsyncSession = Depends(get_db)):
    # Return list of alias strings directly from DB
    result = await db.execute(select(BrokerConfig.alias))
    return [row[0] for row in result.all()]


# Pydantic model for new order request
class NewOrderRequest(BaseModel):
    alias: str
    ticker: str
    action: str  # "BUY" or "SELL"
    quantity: int
    ordertype: str  # e.g., "PositionalOrder"
    price: Optional[float] = 0
    trigger_price: Optional[float] = 0
    stoploss_price: Optional[float] = 0
    stoploss_trigger_price: Optional[float] = 0
    takeprofit_price: Optional[float] = 0
    product: Optional[str] = "MIS"  # MIS, NRML, CNC
    exchange: Optional[str] = None
    validity: Optional[str] = "DAY"
    ordertype_base: Optional[str] = "LIMIT"


@app.post("/place_order")
async def place_order(order: NewOrderRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new order and insert into internalorder table
    """
    try:
        # Validate required fields
        if not order.alias or not order.alias.strip():
            raise HTTPException(status_code=400, detail="Alias is required")
        
        if not order.ticker or not order.ticker.strip():
            raise HTTPException(status_code=400, detail="Ticker is required")
        
        if order.quantity <= 0:
            raise HTTPException(status_code=400, detail="Quantity must be greater than 0")
        
        if order.action.upper() not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="Action must be either BUY or SELL")
        
        # Get broker info from alias
        broker_result = await db.execute(
            select(BrokerConfig).where(BrokerConfig.alias == order.alias)
        )
        broker_config = broker_result.scalar_one_or_none()
        
        if not broker_config:
            raise HTTPException(status_code=404, detail=f"Alias '{order.alias}' not found")
        
        # Validate product
        valid_products = ["MIS", "NRML", "CNC"]
        product = order.product.upper() if order.product else "MIS"
        if product not in valid_products:
            raise HTTPException(status_code=400, detail=f"Product must be one of {valid_products}")
        
        # Create new internal order
        new_order = InternalOrder(
            ordertype=order.ordertype,
            ticker=order.ticker.upper(),
            quantity=order.quantity,
            action=order.action.upper(),
            price=order.price or 0,
            trigger_price=order.trigger_price or 0,
            stoploss_price=order.stoploss_price or 0,
            stoploss_trigger_price=order.stoploss_trigger_price or 0,
            takeprofit_price=order.takeprofit_price or 0,
            broker=broker_config.broker,
            client_id=broker_config.client_id,
            product=product,
            validity=order.validity.upper() if order.validity else "DAY",
            ordertype_base=order.ordertype_base.upper() if order.ordertype_base else "LIMIT",
            entrysingal_source="WEB",
            entry_status="PENDING",
            order_date=date.today(),
            lotsize=1,
            ticksize=0.05,
        )
        
        db.add(new_order)
        await db.commit()
        await db.refresh(new_order)
        
        return {
            "status": "success",
            "message": "Order placed successfully",
            "order_id": new_order.order_id,
            "ticker": new_order.ticker,
            "action": new_order.action,
            "quantity": new_order.quantity,
            "broker": new_order.broker,
        }
    
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        # Rollback on any error
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to place order: {str(e)}")

