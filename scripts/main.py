from json_excel_conversion import *
from custom_cols import get_col_headers
from initialize_data_dict import *
import shutil

if __name__ == "__main__":
    ### STANDARDIZE EXCEL FILES
    directories = [
        'data\\dbo',
    ]
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    # Remove non data dicts from the list

    # files = ['dbo\\DIRS.dbo.PelletGunType_data_dict.xlsx']

    # database_name = 'DIRS'
    for file in files:
        names = file.split("\\")[-1].replace("_data_dict.xlsx", "").split(".")
        database_name = "SLEDSDW"  #names[0]
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
                              custom_col_names=get_col_headers(database_name))
        else:
            shutil.copy(file, output_file)

    # ### INITIALIZE DATA DICTIONARIES
    # # Read in the table names
    # with open('data\\StudentLevelObservations_tables.txt') as f:
    #     tables = [line.strip() for line in f]

    # server = 'EDU-SQLPROD01'
    # database = 'StudentLevelObservations'
    # view = 'dm'

    # for table in tables:
    #     data_dict = initialize_data_dict(server, database, view, table)
    #     json_data = json.dumps(data_dict, indent=4)
    #     file_name = f"data\\initialized\\{database}\\{database}.{view}.{table}_data_dict.xlsx"
    #     os.makedirs(os.path.dirname(file_name), exist_ok=True)
    #     dd_json_to_excel(json_data,
    #                      file_name,
    #                      custom_col_names=get_col_headers(database))

    # ### LIST FILES
    # directories = ['data\\dbo']
    # files = []
    # for directory in directories:
    #     files.extend(list_files(directory))
    # tables = [
    #     file.split("\\")[-1].replace("_data_dict.xlsx", "") for file in files
    # ]
    # for table in tables:
    #     print(table.replace("SLEDSDW.", ""))
