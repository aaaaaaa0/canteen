from sqlalchemy import select
from database.db_tabels import async_session
from database.db_tabels import  Admin


async def set_admin(tg_id: int, chat_id: int):
    async with async_session() as session:
        result = await session.execute(
            select(Admin)
            .where(Admin.tg_id == tg_id))
        admin = result.scalar_one_or_none()
        if not admin:
            session.add(Admin(tg_id=tg_id, chat_id=chat_id))
        else:
            admin.chat_id = chat_id
        await session.commit()
