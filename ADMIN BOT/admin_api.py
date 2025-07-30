from fastapi import FastAPI
from pydantic import BaseModel
from aiogram import Bot
from bot.handlers import notify_admins_about_order 

bot = Bot(token='8202013075:AAGbjRP3wAe89uHJdZZiEHlmrSFqz8xL77k')

app = FastAPI()


class OrderRequest(BaseModel):
    order_id: int


@app.post("/notify")
async def notify_new_order(data: OrderRequest):
    await notify_admins_about_order(data.order_id, bot)
    return {"status": "ok"}
