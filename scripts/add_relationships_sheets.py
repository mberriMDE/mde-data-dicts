from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
from pathlib import Path
import json

def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [str(file) for file in path.rglob(f'*{extension}') if file.is_file()]

# Replace 'your_directory_path' with the path to your directory
files = list_files('SQLPROD01_Standardized')
# file = files[1]

for file in files:
    table_name = file.split("\\")[-1].replace("_data_dict.xlsx", "").replace("_Data_Dictionary.xlsx", "")
    table_name = f"[EDU-SQLPROD01].[{table_name.replace('.', '].[')}]"
    # print(table_name)
    dd = dd_excel_to_json(file)
    json_data = json.loads(dd)
    json_data["Relationships"] = []
    json_str = json.dumps(json_data, indent=4)
    # with open(f'{file.replace(".xlsx", ".json")}', 'w') as f:
    #     f.write(json_str)
    dd_json_to_excel(json_str, file)#f'{file.replace(".xlsx", "2.xlsx")}')


