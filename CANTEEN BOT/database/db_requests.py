from sqlalchemy import select, delete, update, insert
from database.db_tabels import async_session
from database.db_tabels import User, Menu_Section, Product, Cart, Order
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.sql import func
import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")


# Добавить пользователя, если его нет
async def set_user(tg_id: int):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if not user:
            session.add(User(tg_id=tg_id))
            await session.commit()


# Обновить имя пользователя
async def set_user_name(tg_id: int, name: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.name = name
            await session.commit()


# Обновить телефон пользователя
async def set_user_phone(tg_id: int, phone: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.phone = phone
            await session.commit()


# Обновить адрес доставки
async def set_user_address(tg_id: int, address: str):
    async with async_session() as session:
        user = await session.scalar(select(User).where(User.tg_id == tg_id))
        if user:
            user.address = address
            await session.commit()


# Получить все разделы меню
async def get_menu_sections():
    async with async_session() as session:
        result = await session.scalars(select(Menu_Section))
        return result.all()


# Получить продукты по разделу меню
async def get_products_by_menu_section(menu_section_id: int):
    async with async_session() as session:
        result = await session.scalars(select(Product).where(Product.menu_section_id == menu_section_id))
        return result.all()


# Получить продукт по ID
async def get_product_by_id(product_id: int):
    async with async_session() as session:
        return await session.scalar(select(Product).where(Product.id == product_id))


# Получить пользователя по tg_id
async def get_user_by_tg_id(tg_id: int):
    async with async_session() as session:
        return await session.scalar(select(User).where(User.tg_id == tg_id))


# Получить внутренний user.id по tg_id
async def get_internal_user_id(tg_id: int) -> int | None:
    async with async_session() as session:
        return await session.scalar(select(User.id).where(User.tg_id == tg_id))


# Добавить товар в корзину или обновить количество
async def add_to_cart(tg_id: int, product_id: int, quantity: int = 1):
    user_id = await get_internal_user_id(tg_id)
    if not user_id:
        raise ValueError("Пользователь не найден")

    async with async_session() as session:
        cart_item = await session.scalar(
            select(Cart).where((Cart.user_id == user_id) & (Cart.product_id == product_id))
        )
        if cart_item:
            cart_item.quantity += int(quantity)
        else:
            session.add(Cart(user_id=user_id, product_id=product_id, quantity=quantity))
        await session.commit()


# Получить активную корзину пользователя
async def get_cart(tg_id: int):
    user_id = await get_internal_user_id(tg_id)
    if not user_id:
        raise ValueError("Пользователь не найден")

    async with async_session() as session:
        result = await session.execute(
            select(Product.id, Product.name, Product.price, Cart.quantity)
            .join(Cart, Cart.product_id == Product.id)
            .where(Cart.user_id == user_id, Cart.order_id.is_(None))  # 👈 фильтр только активной корзины
        )
        return result.all()





async def clear_cart(user_id: int):
    async with async_session() as session:
        stmt = delete(Cart).where(Cart.user_id == user_id)
        await session.execute(stmt)
        await session.commit()


async def get_menu_section_id_by_product_id(product_id: int) -> int | None:
    async with async_session() as session:
        result = await session.execute(
            select(Product.menu_section_id).where(Product.id == product_id)
        )
        menu_section_id = result.scalar_one_or_none()
        return menu_section_id



async def remove_from_cart(tg_id: int, product_id: int):
    async with async_session() as session:
        user_id = await get_internal_user_id(tg_id)
        if not user_id:
            raise ValueError("Пользователь не найден")
        await session.execute(
            delete(Cart).where(
                Cart.user_id == user_id,
                Cart.product_id == product_id
            )
        )
        await session.commit()


async def update_cart_quantity(user_id: int, product_id: int, quantity: int):
    async with async_session() as session:
        user_id  = await get_internal_user_id(user_id)
        if not user_id:
            raise ValueError("Пользователь не найден")
        await session.execute(
            update(Cart)
            .where(Cart.user_id == user_id, Cart.product_id == product_id)
            .values(quantity=quantity)
        )
        await session.commit()





async def confirm_order(tg_id: int) -> int:
    async with async_session() as session:
        # Получаем внутренний user_id
        user_id = await get_internal_user_id(tg_id)
        if not user_id:
            raise ValueError("Пользователь не найден")

        # Получаем самого пользователя для копирования ФИО, телефона и адреса
        user = await session.scalar(select(User).where(User.id == user_id))
        if not user:
            raise ValueError("Данные пользователя не найдены")

        # Получаем все товары из корзины (без order_id)
        cart_items_result = await session.execute(
            select(Cart).where(Cart.user_id == user_id, Cart.order_id.is_(None))
        )
        cart_items = cart_items_result.scalars().all()
        if not cart_items:
            raise ValueError("Корзина пуста")

        # Подсчитываем сумму, вилки и ложки
        total_price = 0
        total_forks = 0
        total_spoons = 0

        for item in cart_items:
            product_result = await session.execute(
                select(Product).where(Product.id == item.product_id)
            )
            product = product_result.scalar()
            if not product:
                raise ValueError(f"Продукт с id={item.product_id} не найден")

            total_price += int(product.price) * item.quantity
            total_forks += (product.forks or 0) * item.quantity
            total_spoons += (product.spoons or 0) * item.quantity

        # Создаём заказ с копированными данными и подсчитанными приборами
        new_order = Order(
            user_id=user_id,
            total_price=total_price,
            name=user.name,
            phone=user.phone,
            address=user.address,
            forks=total_forks,
            spoons=total_spoons
        )
        session.add(new_order)
        await session.flush()  # Получаем new_order.id

        # Обновляем корзину, чтобы привязать товары к заказу
        await session.execute(
            update(Cart)
            .where(Cart.user_id == user_id, Cart.order_id.is_(None))
            .values(order_id=new_order.id)
        )

        await session.commit()
        return new_order.id
