# from pathlib import Path

# def list_files(directory, extension=".xlsx"):
#     path = Path(directory)
#     return [str(file) for file in path.rglob(f'*{extension}') if file.is_file()]

# db = 'MDEORG'

# files = list_files('SQLPROD01\\'+ db)
# for file in files:
#     table = file.split('\\')[-1].replace('_data_dict.xlsx', '').replace(db + '.', '')
#     print(table)

# from tqdm import tqdm
# import time

# for i in tqdm(range(10), desc='Outer Loop'):
#     for j in tqdm(range(100), desc='Inner Loop', leave=False):
#         time.sleep(0.01)  # Simulate some work
    

str = \
    '''SELECT
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    LEFT(IS_NULLABLE,1) AS IS_NULLABLE'''

print(str)