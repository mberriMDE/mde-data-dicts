import pyodbc
import json
from .json_excel_conversion import dd_json_to_excel, standardize_json
import os
from pathlib import Path
from .custom_cols import get_col_headers


def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [
        str(file) for file in path.rglob(f'*{extension}') if file.is_file()
    ]


def fetch_sql_info(server_name, database_name, view_name, table_name):
    """
    Fetches information about columns in an SQL table.

    Args:
        server_name (str): The name of the server where the database is located.
        database_name (str): The name of the database where the table is located.
        view_name (str): The name of the view/schema where the table is located.
        table_name (str): The name of the table to generate the data dictionary for.

    Returns:
        dict: A dictionary containing information about the server, database, and table.
    """

    connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database_name};Trusted_Connection=yes;"

    try:
        conn = pyodbc.connect(connection_string)
        print("Connection successful!")
    except Exception as e:
        print("Error in connection: ", e)

    # Create a cursor from the connection
    cursor = conn.cursor()
    query = f"SELECT \
                COLUMN_NAME, \
                DATA_TYPE,\
                CHARACTER_MAXIMUM_LENGTH,\
                LEFT(IS_NULLABLE,1) AS IS_NULLABLE\
            FROM \
                INFORMATION_SCHEMA.COLUMNS\
            WHERE \
                TABLE_NAME = '{table_name}' AND TABLE_SCHEMA = '{view_name}'"

    cursor.execute(query)
    print(table_name)
    table_data = {}
    for i, row in enumerate(cursor.fetchall()):
        print(row)
        if row[3] == 'N':
            row_json = {
                "Field Name": row[0],
                "Data Type": row[1],
                "Max Characters": row[2],
                "Null Meaning": row[3]
            }
        else:
            row_json = {
                "Field Name": row[0],
                "Data Type": row[1],
                "Max Characters": row[2]
            }

        table_data[row[0].lower()] = row_json

    return table_data


def initialize_data_dict(server_name,
                         database_name,
                         view_name,
                         table_name,
                         table_type="Data Table",
                         data_dict=None):
    """
    Args:
        server_name (str): The name of the server where the database is located.
        database_name (str): The name of the database where the table is located.
        view_name (str): The name of the view where the table is located.
        table_name (str): The name of the table to generate the data dictionary for.
        data_dict (dict, optional): A dictionary containing the data dictionary for the specified table, if available. Defaults to None.

    Returns:
        dict: A dictionary representing the data dictionary in json format for the specified table.

    """
    new_dict = False
    if data_dict is None:
        data_dict = {
            "Workbook Column Names":
            get_col_headers(database_name),
            "Legend": [],
            "Table Type":
            table_type,
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

    table_info = fetch_sql_info(server_name, database_name, view_name,
                                table_name)

    if new_dict:
        for row in table_info.values():
            data_dict["Data Dictionary"].append(row)
    else:
        remaining_columns = list(table_info.keys())
        for column in data_dict["Data Dictionary"]:
            low = column["Field Name"].lower()
            if low in table_info:
                remaining_columns.remove(low)
                column.update(table_info[low])

        for column in remaining_columns:
            data_dict["Data Dictionary"].append(table_info[column])
    return data_dict


def update_data_dict(server_name, database_name, view_name, table_name,
                     data_dict):
    """
    Updates the data dictionary columns with information from a SQL table.

    Args:
        server_name (str): The name of the server where the database is located.
        database_name (str): The name of the database where the table is located.
        view_name (str): The name of the view where the table is located.
        table_name (str): The name of the table to generate the data dictionary for.
        data_dict (dict): A dictionary containing the data dictionary for the specified table.

    Returns:
        dict: A dictionary representing the updated data dictionary in json format for the specified table.
    """
    table_info = fetch_sql_info(server_name, database_name, view_name,
                                table_name)
    remaining_columns = list(table_info.keys())

    for column in data_dict["Data Dictionary"]:
        low = column["Field Name"].lower()
        if low in table_info:
            column.update(table_info[low])
            remaining_columns.remove(low)

    for column in remaining_columns:
        data_dict["Data Dictionary"].append(table_info[column])

    return data_dict
