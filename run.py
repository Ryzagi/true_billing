import argparse
import asyncio
import os

from pathlib import Path

import MySQLdb
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain
from bot_utils import format_date
from sql import SQLConnection


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--telegram_token", help="Telegram bot token", type=str, required=True
    )
    parser.add_argument(
        "--openai_api_key",
        help="OpenAI API key",
        type=str,
        required=True
    )

    return parser.parse_args()


os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'
SQL_DB = SQLConnection.from_config(Path(os.environ.get('SQL_CONFIG_PATH')))

args = parse_args()
os.environ["OPENAI_API_KEY"] = args.openai_api_key
bot = Bot(token=args.telegram_token)
dispatcher = Dispatcher(bot)

RESTART_KEYBOARD = types.ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton('/start')]], resize_keyboard=True, one_time_keyboard=True
)

# chat history for each session
user_histories = {}


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

    if message.from_user.id not in user_histories:
        user_histories[message.from_user.id] = ConversationBufferWindowMemory(k=3)

    current_history = user_histories[message.from_user.id]

    tables = ['patients', 'facility', 'provider_facility', 'patient_visit', 'patient_visit_cpt', 'patient_visit_icd',
              'case_notes', 'claim', 'users', 'patient_case']

    db = SQLDatabase.from_uri(SQL_DB.get_uri(), include_tables=tables)
    model = 'text-davinci-003'  # 'gpt-3.5-turbo'

    # define model with history
    chatgpt_chain = SQLDatabaseChain(
        llm=OpenAI(model_name=model, temperature=0.00),
        #prompt=template,
        database=db,
        verbose=True,
        memory=current_history,
        top_k=10
    )

    # generate response
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)
    formatted_msg = format_date(message.text)
    #print('\n\n\n', formatted_msg, '\n\n\n')
    try:
        await bot.send_message(message.from_user.id, text=chatgpt_chain.run(formatted_msg))
    except MySQLdb.ProgrammingError:
        await bot.send_message(message.from_user.id, text="Please, rephrase your question")
    except Exception as e:
        print(e)
        await bot.send_message(message.from_user.id, text="Please, provide full date")


if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=False)
