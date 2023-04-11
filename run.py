# Import necessary libraries and modules
import argparse
import asyncio
import os
import MySQLdb

from pathlib import Path
from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import KeyboardButton
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain
from bot_utils import format_date
from sql import SQLConnection


# Define a function to parse command line arguments
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


# Set SQL config path environment variable
os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'

# Define SQL_DB to connect SQL DB
SQL_DB = SQLConnection.from_config(Path(os.environ.get('SQL_CONFIG_PATH')))

# Parse command line arguments
args = parse_args()
os.environ["OPENAI_API_KEY"] = args.openai_api_key

# Create a new bot with the token from command line arguments
bot = Bot(token=args.telegram_token)

# Create a new Dispatcher for the bot
dispatcher = Dispatcher(bot)

# Define a ReplyKeyboardMarkup to show a "start" button
RESTART_KEYBOARD = types.ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton('/start')]], resize_keyboard=True, one_time_keyboard=True
)

# chat history for each session
user_histories = {}


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

    # Check if the user ID is in the user_histories dictionary, if not,
    # initialize a new conversation buffer memory for the user
    if message.from_user.id not in user_histories:
        user_histories[message.from_user.id] = ConversationBufferWindowMemory(k=3)

    # Retrieve the conversation buffer memory for the user
    current_history = user_histories[message.from_user.id]

    # Create a list of tables that are used in the database.
    tables = ['patients', 'facility', 'provider_facility', 'patient_visit', 'patient_visit_cpt', 'patient_visit_icd',
              'case_notes', 'claim', 'users', 'patient_case']

    # Create a SQLDatabaseV2 instance using the SQL_DB.get_uri() and tables list, and save it in the "db" variable
    db = SQLDatabase.from_uri(SQL_DB.get_uri(), include_tables=tables)

    # Define a variable "model" and set its value to "text-davinci-003"
    model = 'text-davinci-003'  # 'gpt-3.5-turbo'

    # Create a SQLDatabaseChainV2 instance and save in the "chatgpt_chain" variable, which takes OpenAI language model,
    # prompt, database, verbose, top_k and return_intermediate_steps as arguments.
    chatgpt_chain = SQLDatabaseChain(
        llm=OpenAI(model_name=model, temperature=0.00),
        database=db,
        verbose=True,
        memory=current_history,
        top_k=10
    )

    # Show a "typing" action to the user
    await bot.send_chat_action(message.from_user.id, action=types.ChatActions.TYPING)

    # Format the request message and pass it to chatgpt_chain to get the chatbot_response
    formatted_msg = format_date(message.text)

    try:
        # If chatbot provides an answer, send it to the user
        await bot.send_message(message.from_user.id, text=chatgpt_chain.run(formatted_msg))
    except MySQLdb.ProgrammingError:
        await bot.send_message(message.from_user.id, text="Please, rephrase your question")
    except Exception as e:
        print(e)
        await bot.send_message(message.from_user.id, text="Please, provide full date")

# Start polling for updates from Telegram
if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=False)
