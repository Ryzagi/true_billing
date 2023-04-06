import csv
from io import StringIO
from typing import Dict, Any, Optional, List
import pandas as pd
from langchain import SQLDatabaseChain, LLMChain, SQLDatabase


class SQLDatabaseChainV2(SQLDatabaseChain):

    @property
    def output_keys(self) -> List[str]:
        """Return the singular output key.

        :meta private:
        """
        if not self.return_intermediate_steps:
            return ["answer"]
        else:
            return ["input_text", "answer", "csv_file", "sql_result", "sql_cmd"]

    def _call(self, inputs: Dict[str, Any]):
        csv_file = ""
        final_result = ""
        llm_chain = LLMChain(llm=self.llm, prompt=self.prompt)
        input_text = f"{inputs[self.input_key]} \nSQLQuery:"
        question = inputs[self.input_key]
        self.callback_manager.on_text(input_text, verbose=self.verbose)
        # If not present, then defaults to None which is all tables.
        table_names_to_use = inputs.get("table_names_to_use")
        table_info = self.database.get_table_info(table_names=table_names_to_use)
        llm_inputs = {
            "input": input_text,
            "top_k": self.top_k,
            "dialect": self.database.dialect,
            "table_info": table_info,
            "stop": ["\nSQLResult:"],
        }
        intermediate_steps = []
        sql_cmd = llm_chain.predict(**llm_inputs)
        intermediate_steps.append(sql_cmd)
        self.callback_manager.on_text(sql_cmd, color="green", verbose=self.verbose)
        result = self.database.run(sql_cmd)
        sql_result = str(result)
        intermediate_steps.append(str(result))
        self.callback_manager.on_text("\nSQLResult: ", verbose=self.verbose)
        self.callback_manager.on_text(str(result), color="yellow", verbose=self.verbose)
        # If return direct, we just set the final result equal to the sql query

        if self.return_direct:
            final_result = str(result)

        elif len(str(result)) > 250:
            print("\n\n\n\n", result, "\n\n\n")
            csv_file = StringIO()
            pd.DataFrame(result).to_csv(csv_file)
            csv_file.seek(0)
            csv_file = csv_file.read()
        else:
            self.callback_manager.on_text("\nAnswer:", verbose=self.verbose)
            input_text += f"{sql_cmd}\nSQLResult: {str(result)}\nAnswer:"
            llm_inputs["input"] = input_text
            final_result = llm_chain.predict(**llm_inputs)
            self.callback_manager.on_text(
                final_result, color="green", verbose=self.verbose
            )
        chain_result: Dict[str, Any] = {self.output_key: final_result}
        if self.return_intermediate_steps:
            chain_result["intermediate_steps"] = intermediate_steps
        print({"answer": chain_result["result"],
                "csv_file": csv_file,
                "sql_result": sql_result,
                "sql_cmd": sql_cmd,
                })

        return {"answer": chain_result["result"],
                "csv_file": csv_file,
                "sql_result": sql_result,
                "sql_cmd": sql_cmd,
                "input_text": question
                }


class SQLDatabaseV2(SQLDatabase):
    def run(self, command: str) -> str:
        """Execute a SQL command and return a string representing the results.

        If the statement returns rows, a string of the results is returned.
        If the statement returns no rows, an empty string is returned.
        """
        with self._engine.begin() as connection:
            if self._schema is not None:
                connection.exec_driver_sql(f"SET search_path TO {self._schema}")
            cursor = connection.exec_driver_sql(command)
            if cursor.returns_rows:
                result = cursor.fetchall()
                return result
        return ""
