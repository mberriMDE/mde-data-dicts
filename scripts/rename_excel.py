from json_excel_conversion import old_dd_excel_to_json, dd_json_to_excel, list_files, standardize_excel, dd_excel_to_json
import json
import os


def rename_excel(file_path, new_name):
    # Read in the old data dictionary
    json_data = dd_excel_to_json(file_path)
    data_dict = json.loads(json_data)

    # Rename the variables entry
    # data_dict["Data Dictionary"] = data_dict.pop("Variables")
    for row in data_dict["Data Dictionary"]:
        # row["Field Name"] = row.pop("Column Name")
        row["Max Characters"] = row.pop("Field Max Length")

    # data_dict["Legend"] = data_dict.pop("Column Descriptions")
    # for row in data_dict["Legend"]:
    #     row["Data Dictionary Column Name"] = row.pop("Column")

    # Write the new data dictionary
    json_data = json.dumps(data_dict)
    dd_json_to_excel(json_data, new_name)


if __name__ == "__main__":
    directory = '1new_SQLPROD01'
    files = list_files(directory)
    for file in files:
        if 'Data_Dicts_Progress' in file:
            continue
        new_name = '1' + file
        new_directory = '\\'.join(new_name.split('\\')[:-1])
        if not os.path.exists(new_directory):
            os.makedirs(new_directory)
        rename_excel(file, new_name)

    files = list_files('1' + directory)
    for file in files:
        standardize_excel(file, file)
