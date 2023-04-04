import argparse
import asyncio
import io
import os

import aiohttp


from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton



def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--telegram_token", help="Telegram bot token", type=str, required=True
    )
    return parser.parse_args()


os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'

args = parse_args()
bot = Bot(token=args.telegram_token)  # args.telegram_token)
dispatcher = Dispatcher(bot)

RESTART_KEYBOARD = types.ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton('/start')]], resize_keyboard=True, one_time_keyboard=True
)


@dispatcher.message_handler(commands=["start"])
async def start(message: types.Message):
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)

    await bot.send_message(
        message.from_user.id,
        text="Hello! Ask your question and I'll answer it!",
        reply_markup=RESTART_KEYBOARD
    )

    await asyncio.sleep(1)


@dispatcher.message_handler()
async def handle_message(message: types.Message) -> None:
    async with aiohttp.ClientSession() as session:
        # Example for MESSAGE_ENDPOINT
        async with session.post(
                "http://localhost:8000/api/ask",
                json={"user_id": message.from_user.id, "message": message.text, "provider_id": None},
        ) as response:
            chatbot_response = await response.json()
            print(chatbot_response)
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)
    if chatbot_response['answer']:
        await bot.send_message(message.from_user.id, text=chatbot_response['answer'])
    else:
        print(chatbot_response['csv_file'])
        csv_data = chatbot_response['csv_file']
        # encode the CSV data as bytes
        csv_bytes = io.BytesIO(csv_data.encode('utf-8'))

        # send the CSV file to the user
        await bot.send_document(
            message.from_user.id,
            document=types.InputFile(csv_bytes,
                                     filename='output.csv')
        )


if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=False)
