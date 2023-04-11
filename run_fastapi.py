# Import necessary libraries and modules
import argparse
import asyncio
import io
import os
import aiohttp

# Import classes and functions from aiogram
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton


# Define a function to parse command line arguments
def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--telegram_token", help="Telegram bot token", type=str, required=True
    )
    return parser.parse_args()


# Set SQL config path environment variable
os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'

# Parse command line arguments
args = parse_args()

# Create a new bot with the token from command line arguments
bot = Bot(token=args.telegram_token)

# Create a new Dispatcher for the bot
dispatcher = Dispatcher(bot)

# Define a ReplyKeyboardMarkup to show a "start" button
RESTART_KEYBOARD = types.ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton('/start')]], resize_keyboard=True, one_time_keyboard=True
)


# Define a handler for the "/start" command
@dispatcher.message_handler(commands=["start"])
async def start(message: types.Message):
    # Show a "typing" action to the user
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)

    # Send a welcome message with a "start" button
    await bot.send_message(
        message.from_user.id,
        text="Hello! Ask your question and I'll answer it!",
        reply_markup=RESTART_KEYBOARD
    )

    # Pause for 1 second
    await asyncio.sleep(1)


# Define a handler for all other messages
@dispatcher.message_handler()
async def handle_message(message: types.Message) -> None:
    async with aiohttp.ClientSession() as session:
        # Example for MESSAGE_ENDPOINT
        # Send a POST request to a chatbot API endpoint with user's message
        async with session.post(
                "http://localhost:8000/api/ask",
                json={"user_id": message.from_user.id, "message": message.text, "provider_id": None},
        ) as response:
            chatbot_response = await response.json()

    # Show a "typing" action to the user
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)

    # If chatbot provides an answer, send it to the user
    if chatbot_response['answer']:
        await bot.send_message(message.from_user.id, text=chatbot_response['answer'])

    # If chatbot provides a CSV file, encode it and send it to the user as a document
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

# Start polling for updates from Telegram
if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=False)
