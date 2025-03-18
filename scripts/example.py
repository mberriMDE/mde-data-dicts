from json_excel_conversion import *
from custom_cols import get_col_headers
from fetch_table_info import *
import shutil

### EXAMPLE USAGE OF DATA DICTIONARY FUNCTIONS.
### PLEASE RUN YOUR OWN USAGE IN A FILE OF YOUR OWN AND MAKE SURE IT IS LISTED IN GITIGNORE.

if __name__ == "__main__":
    ### STANDARDIZE EXCEL FILES
    directories = [
        'data\\dbo',
    ]
    files = []
    for directory in directories:
        files.extend(list_files(directory))

    for file in files:
        names = file.split("\\")[-1].replace("_data_dict.xlsx", "").split(".")
        database_name = "DIRS"  #names[0]
        # find_codes = True if database_name in ['RDMAttributes'] else False
        output_file = file.replace('dbo\\', 'dbo2\\')

        directory = "\\".join(output_file.split("\\")[0:-1])
        if not os.path.exists(directory):
            os.makedirs(directory)

        if '_data_dict.xlsx' in file:
            standardize_excel(file,
                              output_file,
                              make_json=False,
                              find_codes=True,
                              order_codes=True,
                              maintain_columns=True,
                              custom_col_names=get_col_headers(database_name),
                              include_web_sleds_info=True)
        else:
            shutil.copy(file, output_file)

    ### INITIALIZE DATA DICTIONARIES
    # Read in the table names
    with open('data\\rdm_assessments_tables.txt') as f:
        tables = [line.strip() for line in f]

    server = 'EDU-SQLPROD01'
    database = 'Assessments'
    view = 'dbo'
    for table in tables:
        data_dict = initialize_data_dict(server, database, view, table)
        file_name = f"data\\initialized\\{database}\\{database}.{view}.{table}_data_dict.xlsx"
        os.makedirs(os.path.dirname(file_name), exist_ok=True)
        dd_json_to_excel(data_dict, file_name)

    ### LIST FILES
    directories = ['data\\dbo']
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    tables = [
        file.split("\\")[-1].replace("_data_dict.xlsx", "") for file in files
    ]
    for table in tables:
        print(table.replace("SLEDSDW.", ""))

    ### UPDATE DATA DICTIONARIES
    directories = ['data\\update']
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    for file in files:
        table_name = file.split("\\")[-1].replace(
            "_data_dict.xlsx", "").replace("_Data_Dictionary.xlsx", "")
        table_name = f"[EDU-SQLPROD01].[{table_name.replace('.', '].[')}]"
        names = table_name[1:-1].split('].[')
        server_name = names[0]
        database_name = names[1]
        view_name = names[2]
        table_name = names[3]

        print(table_name)
        dd = dd_excel_to_json(file)
        standardized_dd = standardize_json(dd,
                                           find_codes=True,
                                           order_codes=True)
        update_data_dict(server_name, database_name, view_name, table_name,
                         standardized_dd)
        dd_json_to_excel(standardized_dd, file.replace('update', 'updated'))
