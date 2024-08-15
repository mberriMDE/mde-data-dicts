import pyodbc
import json
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import os
from pathlib import Path
from custom_cols import get_col_headers


def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [
        str(file) for file in path.rglob(f'*{extension}') if file.is_file()
    ]


def initialize_data_dict(server_name,
                         database_name,
                         view_name,
                         table_name,
                         data_dict=None):
    """
    Args:
        server_name (str): The name of the server where the database is located.
        database_name (str): The name of the database where the table is located.
        view_name (str): The name of the view where the table is located.
        table_name (str): The name of the table to generate the data dictionary for.

    Returns:
        dict: A dictionary representing the data dictionary in json format for the specified table.

    """
    new_dict = False
    if data_dict is None:
        data_dict = {
            "Workbook Column Names":
            get_col_headers(database_name),
            "Legend": [],
            "Data Dictionary For":
            f"[{server_name}].[{database_name}].[{view_name}].[{table_name}]",
            "FAQs": [{
                "FAQ": "What does each record in the table represent?",
                "Response": ""
            }],
            "Relationships": [],
            "Data Dictionary": []
        }
        new_dict = True

    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database_name};Trusted_Connection=yes;"

    try:
        conn = pyodbc.connect(connection_string)
        print("Connection successful!")
    except Exception as e:
        print("Error in connection: ", e)

    # Create a cursor from the connection
    cursor = conn.cursor()
    cursor.execute(f"SELECT \
                        COLUMN_NAME, \
                        DATA_TYPE,\
                        CHARACTER_MAXIMUM_LENGTH,\
                        LEFT(IS_NULLABLE,1) AS IS_NULLABLE\
                    FROM \
                        INFORMATION_SCHEMA.COLUMNS\
                    WHERE \
                        TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = '{view_name}'"
                   )
    for i, row in enumerate(cursor.fetchall()):
        if row[3] == 'N':
            row_json = {
                "Field Name": row[0],
                "Data Type": row[1],
                "Max Characters": row[2],
                "Null Meaning": row[3]
            }
            # print(row_json)
            if not new_dict:
                data_dict["Data Dictionary"][i]["Null Meaning"] = row_json[
                    "Null Meaning"]
        else:
            row_json = {
                "Field Name": row[0],
                "Data Type": row[1],
                "Max Characters": row[2]
            }
        if new_dict:
            data_dict["Data Dictionary"].append(row_json)

    return data_dict


if __name__ == "__main__":
    files = list_files("RDMPROD01\\RDMESSA")
    tables = []
    for file in files:
        table = file.replace("RDMPROD01\\RDMESSA\\RPT\\RDMESSA.RPT.",
                             "").replace("_data_dict.xlsx", "")
        tables.append(table)
    ### Section to initialize data dictionaries
    server = 'EDU-RDMPROD01'
    database = 'RDMESSA'
    view = 'RPT'
    # tables = files
    for table in tables:
        data_dict = initialize_data_dict(server, database, view, table)
        json_data = json.dumps(data_dict, indent=4)
        file_name = f"{database}\\{database}.{view}.{table}_data_dict.xlsx"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        dd_json_to_excel(json_data,
                         file_name,
                         custom_col_names=get_col_headers(database))

    ### Section to fix the "Null Meaning" column in the data dictionary
    # server_nick = "SQLPROD01"
    # server_name = "EDU-" + server_nick

    # files = list_files(f"new_SQLPROD01")
    # for file in files:
    #     directory = "\\".join(file.split("\\")[:-1])
    #     if not os.path.exists("1"+directory):
    #         os.makedirs("1"+directory)

    #     names = file.split("\\")[-1].replace("_data_dict.xlsx", "").split(".")
    #     database_name = names[0]
    #     view_name = names[1]
    #     table_name = names[2]
    #     # SQLPROD01\Assessments\dbo\Assessments.dbo.Assessment_WIDA_VERIFIED_ACCESS_data_dict.xlsx
    #     # table_name = file.split(
    #     #     "\\")[-1].replace("_data_dict.xlsx", "").split(".")[-1]
    #     # print(table_name)

    #     # Read in current data dictionary
    #     data_dict = None
    #     try:
    #         json_data = dd_excel_to_json(file)
    #         data_dict = json.loads(json_data)
    #     except FileNotFoundError:
    #         print(f"File not found: {file}")

    #     data_dict = initialize_data_dict(
    #         server_name, database_name, view_name, table_name, data_dict=data_dict)
    #     json_data = json.dumps(data_dict, indent=4)

    #     # Convert the data dictionary to an excel file
    #     dd_json_to_excel(json_data, "1"+file,
    #                      custom_col_names=get_col_headers(database_name))