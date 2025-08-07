from sqlalchemy import BigInteger, String, Float, ForeignKey, text, DateTime, func, Boolean
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import time


# Пути и база данных
DB_PATH = "D:\\CANTEEN BOT\\db.sqlite3"


# Движок и сессии
engine = create_async_engine(
    url=f"sqlite+aiosqlite:///{DB_PATH}",
    echo=False,
)
async_session = async_sessionmaker(
    bind=engine,
    expire_on_commit=False  
)


# Базовый класс
class Base(AsyncAttrs, DeclarativeBase):
    pass


# Пользователи
class User(Base):
    __tablename__ = 'Users'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(100), nullable=True)


# Разделы меню
class Menu_Section(Base):
    __tablename__ = 'Menu_Sections'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)


# Продукты
class Product(Base):
    __tablename__ = 'Products'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    price: Mapped[float] = mapped_column(Float, nullable=False)  
    image: Mapped[str] = mapped_column(String(255), nullable=True)
    forks: Mapped[int] = mapped_column(nullable=True)
    spoons: Mapped[int] = mapped_column(nullable=True)
    menu_section_id: Mapped[int] = mapped_column(ForeignKey('Menu_Sections.id'), nullable=False)


# Корзина
class Cart(Base):
    __tablename__ = 'Carts'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('Users.id'), nullable=False)
    product_id: Mapped[int] = mapped_column(ForeignKey('Products.id'), nullable=False)
    quantity: Mapped[int] = mapped_column(nullable=False, default=1)
    order_id: Mapped[int] = mapped_column(ForeignKey('Orders.id'), nullable=False)


# Заказы
class Order(Base):
    __tablename__ = "Orders"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("Users.id"), nullable=False)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total_price: Mapped[int] = mapped_column(BigInteger, nullable=False)
    checks: Mapped[str] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(100), nullable=True)
    phone: Mapped[str] = mapped_column(String(50), nullable=True)
    address: Mapped[str] = mapped_column(String(100), nullable=True)
    forks: Mapped[int] = mapped_column(nullable=True)
    spoons: Mapped[int] = mapped_column(nullable=True)
    notification: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    check_sent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


# Админы
class Admin(Base):
    __tablename__ = 'Admins'

    id: Mapped[int] = mapped_column(primary_key=True)
    tg_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False)
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=True)


# Прием заказов в пользовательском боте
class WorkTime(Base):
    __tablename__ = 'Work_Time'

    id: Mapped[int] = mapped_column(primary_key=True)
    start: Mapped[time] = mapped_column(nullable=False)  
    end: Mapped[time] = mapped_column(nullable=False)
    stop: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


# Для миграции
async def alter_table():
    async with engine.begin() as conn:
        await conn.execute(
            text("ALTER TABLE Paintings ADD COLUMN prediction VARCHAR(100)")
        )
