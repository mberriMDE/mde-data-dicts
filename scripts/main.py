from json_excel_conversion import *
from custom_cols import get_col_headers
from initialize_data_dict import *

if __name__ == "__main__":
    directories = ['data\\RDMESSA']
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    # Remove non from the list
    files = [file for file in files if '_data_dict.xlsx' in file]

    # files = ['dbo\\DIRS.dbo.PelletGunType_data_dict.xlsx']

    database_name = 'DIRS'
    for file in files:
        # directory = "\\".join(file.split("\\")[0:-1])
        # names = file.split("\\")[-1].replace("_data_dict.xlsx", "").split(".")
        # database_name = names[0]
        # find_codes = True if database_name in ['ESSA', 'DIRS'] else False

        standardize_excel(file,
                          file.replace(directory, directory + '2'),
                          make_json=False,
                          find_codes=True,
                          order_codes=True,
                          maintain_columns=True,
                          custom_col_names=get_col_headers(database_name))

    # for file in tqdm(files, desc='Standardizing Excel files'):
    #     directory = "\\".join(file.split("\\")[0:-1])
    #     if not os.path.exists(directory.replace('SQLPROD01', 'SQLPROD01_Standardized')):
    #         os.makedirs(directory.replace('SQLPROD01', 'SQLPROD01_Standardized'))
    #     standardize_excel(file, file.replace('SQLPROD01', 'SQLPROD01_Standardized'), make_json=False, find_codes=False, order_codes=False)

    # file = 'oMDEORG.apilegacy.DBORGUNIT_data_dict.xlsx'
    # standardize_excel(file, file[1:], make_json=False, find_codes=True, order_codes=True)
