
import asyncio
import os
from pathlib import Path

import MySQLdb


from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain, PromptTemplate
from starlette.responses import PlainTextResponse

from bot_utils import format_date
from data import Message
from sql import SQLConnection
from datetime import datetime
from fastapi import FastAPI, Response, status, HTTPException
os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'

app = FastAPI()

SQL_DB = SQLConnection.from_config(Path(os.environ.get('SQL_CONFIG_PATH')))
MESSAGE_ENDPOINT = "/api/ask"
# chat history for each session
user_histories = {}
attending_provider_id = None


@app.post(MESSAGE_ENDPOINT)
async def handle_message(request: Message) -> PlainTextResponse:

    if request.user_id not in user_histories:
        user_histories[request.user_id] = ConversationBufferWindowMemory(k=3)

    current_history = user_histories[request.user_id]

    if isinstance(request.attending_provider_id, int):
        _DEFAULT_TEMPLATE = f"""Given the attending_provider_id = {request.attending_provider_id} this 
        attending_provider_id means, that i need results filtered by this attending_provider_id.You are a doctor 
        assistant with attending_provider_id = {request.attending_provider_id} bot of the True Billing company. Your 
        task is to use the database to give accurate answers to user requests. Answer the following questions as best 
        you can. Given an input question, first create a syntactically correct {{dialect}} query to run, then look at 
        the results of the query and return the answer. Unless the user specifies in his question a specific number 
        of examples he wishes to obtain, always limit your query to at most {{top_k}} results using the LIMIT clause. 
        You can order the results by a relevant column to return the most interesting examples in the database. Pay 
        attention to use only the column names that you can see in the schema description. Be careful to not query 
        for columns that do not exist. Also, pay attention to which column is in which table. Use the following 
        format: Question: "Question here" SQLQuery: "SQL Query to run" SQLResult: "Result of the SQLQuery" Answer: 
        "Final answer here" Only use the following tables: {{table_info}} Question: {{input}} """
    else:
        _DEFAULT_TEMPLATE = """ You are a doctor assistant bot of the True Billing company. Your task is to use the 
        database to give accurate answers to user requests. Answer the following questions as best you can. Given an 
        input question, first create a syntactically correct {dialect} query to run, then look at the results of 
        the query and return the answer. Unless the user specifies in his question a specific number of examples he 
        wishes to obtain, always limit your query to at most {top_k} results using the LIMIT clause. You can order 
        the results by a relevant column to return the most interesting examples in the database. Pay attention to 
        use only the column names that you can see in the schema description. Be careful to not query for columns 
        that do not exist. Also, pay attention to which column is in which table. Use the following format: Question: 
        "Question here" SQLQuery: "SQL Query to run" SQLResult: "Result of the SQLQuery" Answer: "Final answer here" 
        Only use the following tables: {table_info} Question: {input} """

    prompt = PromptTemplate(
        input_variables=["input", "table_info", "dialect", "top_k"],
        template=_DEFAULT_TEMPLATE,
    )

    tables = ['patients', 'facility', 'provider_facility', 'patient_visit', 'patient_visit_cpt', 'patient_visit_icd',
              'case_notes', 'claim', 'users', 'patient_case']

    db = SQLDatabase.from_uri(SQL_DB.get_uri(), include_tables=tables)
    model = 'text-davinci-003'  # 'gpt-3.5-turbo'

    chatgpt_chain = SQLDatabaseChain(
            llm=OpenAI(model_name=model, temperature=0.00),
            prompt=prompt,
            database=db,
            verbose=True,
            memory=current_history,
            top_k= 10
         )

    formatted_msg = format_date(request.message)

    try:
        return PlainTextResponse(chatgpt_chain.run(formatted_msg))
    except MySQLdb.ProgrammingError:
        return PlainTextResponse("Please, rephrase your question")
    except Exception as e:
        return PlainTextResponse("Please, provide full date")

