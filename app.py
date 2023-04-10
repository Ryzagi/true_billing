import os
import os.path
import csv

from pathlib import Path
from typing import Dict
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain import OpenAI, SQLDatabase, SQLDatabaseChain, PromptTemplate
from bot_utils import format_date
from data import Message
from langchainV2 import SQLDatabaseChainV2, SQLDatabaseV2
from sql import SQLConnection

from fastapi import FastAPI, Response, status, HTTPException
os.environ['SQL_CONFIG_PATH'] = 'configs/sql_config.json'

app = FastAPI()

SQL_DB = SQLConnection.from_config(Path(os.environ.get('SQL_CONFIG_PATH')))
MESSAGE_ENDPOINT = "/api/ask"
# chat history for each session
user_histories = {}


@app.post(MESSAGE_ENDPOINT)
async def handle_message(request: Message) -> Dict:

    if request.user_id not in user_histories:
        user_histories[request.user_id] = ConversationBufferWindowMemory(k=3)

    current_history = user_histories[request.user_id]

    if isinstance(request.provider_id, int):
        template = f"""You are a doctor with given an attending_provider_id = {request.provider_id}.
Return results filtered by pa_id from providers_supervisers table where provider_id = {request.provider_id}. Your 
task is to use the database to give accurate answers to user requests.All names in question are patients and visitors 
names.If given name of the patient then filter results by this name.Answer the following questions as best you can. 
Given an input question, first create a syntactically correct {{dialect}} query to run, then look at the results of 
the query and return the answer. Unless the user specifies in his question a specific number of examples he wishes to 
obtain, always limit your query to at most {{top_k}} results using the LIMIT clause. You can order the results by a 
relevant column to return the most interesting examples in the database. Pay attention to use only the column names 
that you can see in the schema description. Be careful to not query for columns that do not exist. Also, 
pay attention to which column is in which table. Use the following format: Question: "Question here" SQLQuery: "SQL 
Query to run" SQLResult: "Result of the SQLQuery" Answer: "Final answer here" Only use the following tables: 
{{table_info}} Question: {{input}} """
    else:
        template = """ You are a doctor assistant bot of the True Billing company. Your task is to use the 
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
        template=template,
    )

    tables = ['patients', 'facility', 'provider_facility', 'patient_visit', 'patient_visit_cpt', 'patient_visit_icd',
              'case_notes', 'claim', 'users', 'patient_case', 'providers_supervisers']

    db = SQLDatabaseV2.from_uri(SQL_DB.get_uri(), include_tables=tables)
    model = 'text-davinci-003'  # 'gpt-3.5-turbo'

    chatgpt_chain = SQLDatabaseChainV2(
            llm=OpenAI(model_name=model, temperature=0.00,max_retries=1, max_tokens=-1),
            prompt=prompt,
            database=db,
            verbose=True,
            top_k=10,
            return_intermediate_steps=True,

         )

    formatted_msg = format_date(request.message)
    chatbot_response = chatgpt_chain(formatted_msg)

    # CSV SAVING

    #filename = 'logs.csv'
    ## check if file exist, then append new rows
    #if os.path.isfile(filename):
    #    with open(filename, 'a', newline='') as file:
    #        fieldnames = ["input_text", 'answer', 'sql_result', "sql_cmd", 'csv_file']
    #        writer = csv.DictWriter(file, fieldnames=fieldnames)
    #        writer.writerow({"input_text":chatbot_response["input_text"],
    #                        "answer": chatbot_response["answer"],
    #                         "sql_result": chatbot_response["sql_result"],
    #                         'sql_cmd': chatbot_response["sql_cmd"],
    #                         "csv_file": chatbot_response["csv_file"]
    #                         }
    #                    )
    #else:
    #    # create new file and write headers and rows
    #    with open(filename, 'w', newline='') as file:
    #        fieldnames = ["input_text", 'answer', 'sql_result', "sql_cmd", 'csv_file']
    #        writer = csv.DictWriter(file, fieldnames=fieldnames)
    #        writer.writeheader()
    #        writer.writerow({"input_text": chatbot_response["input_text"],
    #                         "answer": chatbot_response["answer"],
    #                         "sql_result": chatbot_response["sql_result"],
    #                         'sql_cmd': chatbot_response["sql_cmd"],
    #                         "csv_file": chatbot_response["csv_file"]
    #                         }
    #
    #                        )

    # TXT SAVING
    filename = 'logging.txt'

    if os.path.isfile(filename):
        with open(filename, 'a') as file:
            file.write(chatbot_response["input_text"] + "\n" + chatbot_response["sql_cmd"] + "\n" +
                       chatbot_response["sql_result"] + "\n" + chatbot_response["answer"] + "\n" +
                       chatbot_response["csv_file"] + "\n\n")
    else:
        with open(filename, 'w') as file:
            file.write(chatbot_response["input_text"] + "\n" + chatbot_response["sql_cmd"] + "\n" +
                       chatbot_response["sql_result"] + "\n" + chatbot_response["answer"] + "\n" +
                       chatbot_response["csv_file"] + "\n\n")
    return chatbot_response

