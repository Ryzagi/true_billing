import argparse
import asyncio
import os

from pathlib import Path
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

    # Define the prompt template
    template = """You are a doctor assistant bot of the True Billing company. Your task is to use the database to give 
    accurate answers to user requests. Answer the following questions as best you can. 

    Given an input question, first create a syntactically correct query to run, then look at the results of 
    the query and return the answer. Unless the user specifies in his question a specific number of examples he 
    wishes to obtain, always limit your query to at most top_k results. You can order the results by a relevant 
    column to return the most interesting examples in the database. Never query for all the columns from a specific 
    table, only ask for a the few relevant columns given the question. Pay attention to use only the column names 
    that you can see in the schema description. Be careful to not query for columns that do not exist. Also, 
    pay attention to which column is in which table. 

    User: {query}
    Doctor assistant: """

    # define prompt with template
    #prompt = PromptTemplate(
    #    input_variables=["query"],
    #    template=template
    #)

    tables = ['patients', 'facility', 'provider_facility', 'patient_visit', 'patient_visit_cpt', 'patient_visit_icd']

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
    print('\n\n\n', formatted_msg, '\n\n\n')
    try:
        await bot.send_message(message.from_user.id, text=chatgpt_chain.run(formatted_msg))
    except Exception as e:
        print(e)
        await bot.send_message(message.from_user.id, text="Please, provide full date")


if __name__ == "__main__":
    executor.start_polling(dispatcher, skip_updates=False)
