from sqlalchemy import Column, String, Integer, Boolean, Numeric, Date, BigInteger,Enum,DateTime,func,ForeignKey,Index
from database import Base
from sqlalchemy.orm import relationship

class Order(Base):
    __tablename__ = "orders"

    order_id = Column(BigInteger, primary_key=True, autoincrement=False)
    ticker = Column(String(64), nullable=False)
    client_id = Column(String(64), nullable=False)
    broker = Column(String(64), nullable=False)
    brokeraccount = Column(String(32), nullable=False)
    product = Column(String(32))
    action = Column(String(8))
    quantity = Column(Integer)
    quantity_filled = Column(Integer)
    quantity_exited = Column(Integer)
    entry_status = Column(String(32))
    exit_status = Column(String(32))
    date_entrylast = Column(Date)
    date_exit = Column(Date)
    price = Column(Numeric(18, 6))
    stoploss_price = Column(Numeric(18, 6))
    takeprofit_price = Column(Numeric(18, 6))
    equity = Column(Numeric(20, 6))

class BrokerConfig(Base):
    __tablename__ = "brokerconfig"

    broker_account = Column(String(64), primary_key=True)
    alias = Column(String(64), unique=True, index=True, nullable=False)
    broker = Column(String(64), nullable=False)
    client_id = Column(String(64), nullable=False)

class InternalOrder(Base):
    __tablename__ = "internalorder"

    order_id = Column(BigInteger, primary_key=True, autoincrement=True)

    ordertime = Column(DateTime(timezone=False), default=func.now())
    last_updated = Column(DateTime(timezone=False), default=func.now(), onupdate=func.now())

    ordertype = Column(String(32), nullable=False)
    ticker = Column(String(64), nullable=False)
    quantity = Column(Integer)
    action = Column(Enum("BUY", "SELL", name="io_action_enum"), nullable=False)
    price = Column(Numeric(10, 4), default=0)
    trigger_price = Column(Numeric(10, 4), default=0)

    fixed_stoploss_points = Column(Numeric(10, 4), default=0)
    trailing_stoploss_points = Column(Numeric(10, 4), default=0)
    take_profit_points = Column(Numeric(10, 4), default=0)

    takeprofit_price = Column(Numeric(10, 4), default=0)
    stoploss_price = Column(Numeric(10, 4), default=0)

    broker = Column(
        Enum(
            "ZERODHA","IIFL","DUMMYAJITA","DUMMYAJITB","PAPER","PAISA5","NBANG","ASIATIC",
            "KOTAK","CEDGE","BIGUL","SSCOR","REDBLU","MOTILAL","MARWADI","VIKABH","DBINT",
            "GYAN","FINDOC","SHARE","VTCAP","SDEVA","BLB","BRSB","GRD","JNAM","ARHM","MADV",
            "ACA","PASPATI","SYMPHONY","MTRUST","PACE","MAVRIK","GLOBE","SMC","ADROIT",
            "NAVJN","PRB","TORUS","RELIANCE","ABIRA","KARNA","EMKAY","ANS","ACHINT",
            "WISDOM","DHANI","CHOICE","MLB","SUNRISE","ANGEL",
            name="internalorder_broker_enum"
        ),
        nullable=False
    )

    parent_order_id = Column(BigInteger, ForeignKey("internalorder.order_id"))

    lotsize = Column(Integer, default=1)
    ticksize = Column(Numeric(10, 4), default=0.05)

    broker_order_tag = Column(BigInteger)
    broker_parent_order_id = Column(Integer)

    twap_leg_count = Column(Integer, default=0)
    twap_leg_no = Column(Integer, default=0)

    time_in_force = Column(String(16))
    exit_time = Column(String(16))

    entry_status = Column(String(30))
    exit_status = Column(String(30))

    remarks = Column(String(64))
    strategy_id = Column(String(64))
    dealer_id = Column(String(16))
    client_id = Column(String(16))

    currency = Column(String(3))

    quantity_filled = Column(Integer, default=0)
    quantity_exited = Column(Integer, default=0)

    entrysingal_source = Column(Enum("ALGO","WEB", name="entry_signal_enum"))
    exit_status_tp = Column(String(30))
    exitsignal_source = Column(Enum("ALGO","WEB", name="exit_signal_enum"))

    isactive_exit = Column(Integer, default=0)

    multileg = Column(Enum("TWAP","VWAP", name="multileg_enum"))
    orderexit_how = Column(Enum("TP","SL","EOD","MANUAL","ALGO","UNKNOWN", name="orderexit_how_enum"))

    ordertype_base = Column(Enum("LIMIT","MARKET","SL","SL-M", name="ot_base_enum"))
    ordertype_base_exit = Column(Enum("LIMIT","MARKET","SL","SL-M", name="ot_base_exit_enum"))
    product = Column(Enum("CNC","NRML","MIS", name="product_io_enum"))

    signal_id = Column(BigInteger, default=0)

    slippageprice_entry = Column(Numeric(10, 4), default=0)
    slippageprice_exit = Column(Numeric(10, 4), default=0)

    stoploss_trigger_price = Column(Numeric(10, 4), default=0)

    time_in_force_exit_sl = Column(String(16))
    time_in_force_exit_tp = Column(String(16))

    validity = Column(Enum("IOC","DAY","EOS", name="validity_enum"))
    validity_exit = Column(Enum("IOC","DAY","EOS", name="validity_exit_enum"))

    variety = Column(Enum("AMO","INTRADAY","OVERNIGHT", name="variety_enum"))
    variety_exit = Column(Enum("AMO","INTRADAY","OVERNIGHT", name="variety_exit_enum"))

    date_entrylast = Column(Date)
    date_exit = Column(Date)
    time_entrystart = Column(String(16))

    equity = Column(Numeric(12, 2), default=0)

    market = Column(Enum("CASH","FUTURES","OPTIONS", name="market_enum"))

    monitor_sltrigger = Column(Numeric(10, 4))
    monitor_trigger = Column(Numeric(10, 4))

    brokeraccount = Column(Integer)

    order_date = Column(Date)
    last_updated_date = Column(Date)


class BrokerOrder(Base):
    __tablename__ = "brokerorder"

    id = Column(Integer, primary_key=True, autoincrement=True)
    average_price = Column(Numeric(10, 4))
    disclosed_quantity = Column(Integer)
    exchange = Column(String(8), nullable=False)
    exchange_order_id = Column(String(50))
    exchange_timestamp = Column(DateTime(timezone=False), default=func.now())
    exchange_update_timestamp = Column(DateTime(timezone=False), default=func.now())
    filled_quantity = Column(Integer)
    instrument_token = Column(BigInteger)
    order_id = Column(String(20))
    order_timestamp = Column(DateTime(timezone=False), default=func.now())
    order_type = Column(String(10))
    parent_order_id = Column(String(20))
    pending_quantity = Column(Integer)
    placed_by = Column(String(10))
    price = Column(Numeric(10, 4))
    product = Column(String(10))
    quantity = Column(Integer)
    status = Column(String(16))
    status_message = Column(String(64))
    tag = Column(BigInteger)
    tradingsymbol = Column(String(64))
    transaction_type = Column(String(6))
    trigger_price = Column(Numeric(10, 4))
    validity = Column(String(10))
    variety = Column(String(10))

    broker = Column(
        Enum(
            "ZERODHA","IIFL","DUMMYAJITA","DUMMYAJITB","PAPER","PAISA5","NBANG","ASIATIC",
            "KOTAK","CEDGE","BIGUL","SSCOR","REDBLU","MOTILAL","MARWADI","VIKABH","DBINT",
            "GYAN","FINDOC","SHARE","VTCAP","SDEVA","BLB","BRSB","GRD","JNAM","ARHM","MADV",
            "ACA","PASPATI","SYMPHONY","MTRUST","PACE","MAVRIK","GLOBE","SMC","ADROIT",
            "NAVJN","PRB","TORUS","RELIANCE","ABIRA","KARNA","EMKAY","ANS","ACHINT",
            "WISDOM","DHANI","CHOICE","MLB","SUNRISE",
            name="broker_enum"
        ),
        nullable=False
    )

    client_id = Column(String(10))
    brokeraccount = Column(Integer)

    # Cannot auto-generate SQL computed columns in PostgreSQL easily → store as real column
    orderdate = Column(Date)


Index("ix_order_timestamp_brokerorder", BrokerOrder.order_timestamp)
Index("ix_order_timestamp_status_brokerorder", BrokerOrder.order_timestamp, BrokerOrder.status)
Index("ix_order_timestamp_tag_brokerorder", BrokerOrder.order_timestamp, BrokerOrder.tag)
Index("ix_order_timestamp_tradingsymbol_brokerorder", BrokerOrder.order_timestamp, BrokerOrder.tradingsymbol)
Index("ix_exchange_timestamp_brokeraccount_brokerorder", BrokerOrder.exchange_timestamp, BrokerOrder.brokeraccount, BrokerOrder.tradingsymbol)

class Trade(Base):
    __tablename__ = "trade"

    trade_primarykey_id = Column(Integer, primary_key=True, autoincrement=True)
    exchange_timestamp = Column(DateTime(timezone=False), nullable=False)
    ticker = Column(String(64), nullable=False)
    exchange = Column(String(8), nullable=False)

    action = Column(Enum("BUY", "SELL", name="action_enum"), nullable=False)

    price = Column(Numeric(10, 4), nullable=False)
    exchange_order_id = Column(BigInteger, nullable=False)
    broker_order_id = Column(BigInteger, nullable=False)
    broker_trade_id = Column(BigInteger, nullable=False)
    internalorder_id = Column(BigInteger, ForeignKey("internalorder.order_id"))

    quantity = Column(Integer, nullable=False)

    broker = Column(
        Enum(
            "ZERODHA","IIFL","DUMMYAJITA","DUMMYAJITB","PAPER","PAISA5","NBANG","ASIATIC",
            "KOTAK","CEDGE","BIGUL","SSCOR","REDBLU","MOTILAL","MARWADI","VIKABH","DBINT",
            "GYAN","FINDOC","SHARE","VTCAP","SDEVA","BLB","BRSB","GRD","JNAM","ARHM","MADV",
            "ACA","PASPATI","SYMPHONY","MTRUST","PACE","MAVRIK","GLOBE","SMC","ADROIT",
            "NAVJN","PRB","TORUS","RELIANCE","ABIRA","KARNA","EMKAY","ANS","ACHINT",
            "WISDOM","DHANI","CHOICE","MLB","SUNRISE",
            name="trade_broker_enum"
        ),
        nullable=False
    )

    brokerage_charge = Column(Numeric(10, 4), default=0)
    exchange_charge = Column(Numeric(10, 4), default=0)
    gst_charge = Column(Numeric(10, 4), default=0)
    stt_charge = Column(Numeric(10, 4), default=0)
    stampduty_charge = Column(Numeric(10, 4), default=0)
    sebi_charge = Column(Numeric(10, 4), default=0)
    other_charge = Column(Numeric(10, 4), default=0)

    client_id = Column(String(16))
    is_exercise = Column(Integer, default=0)
    brokeraccount = Column(Integer)

    product = Column(Enum("MIS","NRML","CNC","BO","CO", name="product_enum"))

    clearing_charge = Column(Numeric(10, 4), default=0)
    brokerage_fix_charge = Column(Numeric(10, 4), default=0)
    fixed_charges_other = Column(Numeric(10, 4), default=0)

    # Not using virtual date column in PostgreSQL, store directly
    exchange_timestamp_date = Column(Date)

