from sqlalchemy import Column, String, Integer, Boolean, Numeric, Date, BigInteger
from database import Base

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
