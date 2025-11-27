from fastapi import FastAPI, Depends, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select,func
from pydantic import BaseModel
from datetime import datetime, date
import datetime
import threading
import subprocess
import sys
import signal
import atexit
import aio_pika

from database import get_db, engine, Base, AsyncSessionLocal
from models import Order, BrokerConfig,InternalOrder,BrokerOrder,Trade
from auth import LoginRequest, TokenResponse, create_access_token, verify_token
import deccan_execution_handler.events as eventk
from deccan_execution_handler.price_parser import PriceParser
from deccan_execution_handler.message_pack import MsgpackKanhoji

app = FastAPI(title="Positions Readonly API")

RABBITMQ_URL = "amqp://deccan:Deccan115@127.0.0.1:5672/"
OMS_QUEUE = "kanhoji.to.orderbook_handler_worker.1"
EXCHANGE_NAME = "kanhoji_worker"

broker_configs = {}  # alias → broker config mapping

# Background processes
worker_process = None
consumer_thread = None
shutdown_flag = threading.Event()

async def load_broker_configs():
    """Load broker configurations into memory on startup."""
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(BrokerConfig))
        rows = result.scalars().all()
        for row in rows:
            broker_configs[row.alias] = {
                "broker": row.broker,
                "client_id": row.client_id,
                "broker_account": row.broker_account,
            }
    print(f"✅ Loaded {len(broker_configs)} broker configs")

def cleanup_processes():
    """Cleanup all background processes"""
    global worker_process, consumer_thread
    
    print("🧹 Cleaning up background processes...")
    
    # Terminate Celery worker
    if worker_process and worker_process.poll() is None:
        print("⏹️ Stopping Celery worker...")
        worker_process.terminate()
        try:
            worker_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            worker_process.kill()
    
    # Signal consumer thread to stop
    shutdown_flag.set()
    
    print("✅ Cleanup complete")

# Register cleanup on exit
atexit.register(cleanup_processes)

def start_celery_worker():
    """Start Celery worker as subprocess"""
    global worker_process
    worker_process = subprocess.Popen([
        sys.executable, "-m", "celery",
        "-A", "celery_app", "worker",
        "--loglevel=info",
        "--pool=solo",
        "--queues=celery_tasks"
    ])

def start_rabbitmq_consumer():
    """Start RabbitMQ consumer in background thread"""
    from celery_middleware import main as consumer_main
    try:
        consumer_main()
    except Exception as e:
        if not shutdown_flag.is_set():
            print(f"❌ Consumer error: {e}")

@app.on_event("startup")
async def startup_event():
    """Start Celery worker and RabbitMQ consumer on app startup"""
    global worker_process, consumer_thread
    
    print("🚀 Starting Celery worker...")
    start_celery_worker()
    
    print("🚀 Starting RabbitMQ consumer...")
    consumer_thread = threading.Thread(target=start_rabbitmq_consumer, daemon=False)
    consumer_thread.start()
    
    print("✅ All background services started")
   

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Load broker configs into memory
    await load_broker_configs()

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    print("🛑 Shutting down background services...")
    cleanup_processes()

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
        "endpoints": ["/health", "/positions_json", "/aliases","/internal_order","/broker_order","/trades","/login","/place_order"],
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
async def place_order(request: Request, db: AsyncSession = Depends(get_db)):
    data = await request.json()

    # Lookup client_id, broker, brokeraccount based on alias
    alias = data.get("alias")
    client_id = broker = brokeraccount = None
    if alias:
        query = select(Order).where(Order.client_id == alias).limit(1)
        result = await db.execute(query)
        order = result.scalars().first()
        if order:
            client_id = order.client_id
            broker = order.broker
            brokeraccount = order.brokeraccount
    broker_info = broker_configs[alias]
    # Build the signal payload
    # parse time_in_force into a datetime.time object
    time_str = data.get("time_in_force", "15:31")
    try:
        time_in_force = datetime.datetime.strptime(time_str, "%H:%M").time()
    except Exception:
        # fallback to default if parsing fails
        time_in_force = datetime.datetime.strptime("15:31", "%H:%M").time()
    if data.get("price") in [None, 0, "0", ""]:
        data["price"] = None
    else:
        data["price"] = PriceParser.parse(float(data["price"]))
    if data.get("trigger_price") in [None, 0, "0", ""]:
        data["trigger_price"] = None
    else:
        data["trigger_price"] = PriceParser.parse(float(data["trigger_price"]))     
    if data.get("stoploss_price") in [None, 0, "0", ""]:
        data["stoploss_price"] = None
    else:
        data["stoploss_price"] = PriceParser.parse(float(data["stoploss_price"]))
    if data.get("stoploss_trigger_price") in [None, 0, "0", ""]:
        data["stoploss_trigger_price"] = None
    else:
        data["stoploss_trigger_price"] = PriceParser.parse(float(data["stoploss_trigger_price"]))   
    if data.get("takeprofit_price") in [None, 0, "0", ""]:
        data["takeprofit_price"] = None
    else:
        data["takeprofit_price"] = PriceParser.parse(float(data["takeprofit_price"]))
    payload = {
        "signal_id": int(datetime.datetime.now().timestamp() * 1000),
        "exchange": data.get("exchange","NFO"),
        "type": "SIGNAL",
        "signaltype": "NEW_ENTRY",
        "ticker": data.get("ticker"),
        "quantity": int(data.get("quantity", 0)),
        "action": data.get("action"),
        "broker": broker_info.get("broker") or data.get("broker"),
        "client_id": broker_info.get("client_id") or data.get("client_id"),
        "brokeraccount": broker_info.get("broker_account") or data.get("brokeraccount"),
        "price": data.get("price", 0),
        "trigger_price": data.get("trigger_price", 0),
        "stoploss_price": data.get("stoploss_price", 0),
        "stoploss_trigger_price": data.get("stoploss_trigger_price", 0),
        "takeprofit_price": data.get("takeprofit_price", 0),
        "product": data.get("product"),
        "ordertype": data.get("ordertype"),
        "strategy_id": "POTN3",
        "dealer_id": "MANGESH",
        "currency": "INR",
        "time_in_force": time_in_force,
        "variety": "OVERNIGHT",
        "validity": "DAY",
        "market": "OPTIONS",
        "isactive_exit": True,
        "lotsize": int(data.get("lotsize", 1)),
        "ticksize": PriceParser.parse(float(data.get("ticksize", 0.05))),
        "parent_order_id": None,
        'time_in_force': datetime.time(23, 31),
        "variety": "OVERNIGHT",
        "validity": "DAY",
        'entrysingal_source': 'ALGO', 
        'exitsignal_source': 'ALGO', 
        'slippageprice_entry': 0, 
        'slippageprice_exit': 0, 
        'orderexit_how': 'ALGO', 
        'equity': 100000.0,
        'time_entrystart': datetime.time(9, 15),
        'date_entrylast': datetime.date(2027, 10, 23),
        'date_exit': datetime.datetime(2027, 10, 23, 0, 0),
        'twap_leg_count': 1,
        'exit_time': datetime.time(16, 0),

    }

    # Send to RabbitMQ
    try:
        connection = await aio_pika.connect_robust(RABBITMQ_URL)

        async with connection:
            channel = await connection.channel()
            await channel.set_qos(prefetch_count=1)

            # Declare exchange if not already existing
            exchange = await channel.declare_exchange(EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=False)

            # Create the message payload
            signal_event = eventk.SignalEvent(**payload)
            packed_data = MsgpackKanhoji.packb(signal_event)

            # Publish to exchange with routing key
            message = aio_pika.Message(
                body=packed_data,
                delivery_mode=aio_pika.DeliveryMode.PERSISTENT
            )

            await exchange.publish(message, routing_key=OMS_QUEUE)
            print(f"✅ Message published to exchange '{EXCHANGE_NAME}' with routing '{OMS_QUEUE}'")


    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)})

    return JSONResponse({"status": "success"})