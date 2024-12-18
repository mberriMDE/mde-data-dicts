import pandas as pd
import json
import os
import pyodbc
from tqdm import tqdm
from pathlib import Path
from custom_cols import get_col_headers
from add_web_sleds_info import add_web_sleds_info

# Function to truncate a string to 31 characters for worksheet names


def trunc31(string):
    if len(string) > 31:
        return string[:31]
    return string


def initialize_code_sheet(current_rows,
                          server_name,
                          database_name,
                          view_name,
                          table_name,
                          field_name,
                          find_codes=True,
                          order_codes=False):
    '''
    Selects the distinct values from a field in a table and creates a data dictionary for the field.

    Args:
        current_rows (dict): A dictionary of the current rows in the field. (key is the code)
        server_name (str): The name of the server where the database is located.
        database_name (str): The name of the database where the table is located.
        view_name (str): The name of the view where the table is located.
        table_name (str): The name of the table to generate the data dictionary for.

    Returns:
        dict_list (list): A list of dictionaries representing the data dictionary code sheet in json 
        format for the specified field.
    '''
    dict_list = []
    current_codes = []

    if find_codes:
        connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database_name};Trusted_Connection=yes;"

        try:
            conn = pyodbc.connect(connection_string)
        except Exception as e:
            print("Error in connection: ", e)

        # Create a cursor from the connection
        cursor = conn.cursor()
        cursor.execute(
            f"SELECT DISTINCT [{field_name}] FROM [{database_name}].[{view_name}].[{table_name}] ORDER BY [{field_name}]"
        )

        codes_in_data = []

        for row in cursor:
            code = row[0]
            if code == "NULL":
                code = '"NULL"'
            if pd.isnull(code):
                code = "NULL"
            if isinstance(code, bool):
                code = 1 if code else 0
            code = str(code).strip()
            if code == "":
                code = "Blank"
            # If the code is not already in the code list, add it to the dictionary list
            if code not in current_rows:
                dict_list.append({
                    "Code": code,
                    "Description": "",
                    "Reporting Status": "",
                    "In Data": "Y",
                    "Notes": "",
                })
                current_codes.append(code)
            codes_in_data.append(code)

    # Add the remaining rows to the dictionary list
    for key, value in current_rows.items():
        if key not in current_codes:
            dict_list.append(value)

    if find_codes:
        # Mark whether the code is in the data or not
        for value in dict_list:
            if value['Code'] in codes_in_data:
                value['In Data'] = 'Y'
            else:
                value['In Data'] = 'N'

    # Custom sort key function
    def custom_sort_key(item):
        '''
        A custom sort key function to sort the dictionary list by the code in a readable way.
        - The integer codes appear before the other codes. 
        - The integer codes are sorted by their ascending integer value, not their string value. 
        - NULL and Blank are at the top of the list.
        '''
        code = item['Code']
        if code == "NULL":
            return (0, '')
        elif code == "Blank":
            return (1, '')
        elif code.isdigit():
            return (2, int(code))
        else:
            return (3, code)

    if order_codes:
        # Sort the dictionary list by the custom sort key
        dict_list = sorted(dict_list, key=custom_sort_key)

    return dict_list


def get_legend(data_dict_headers):
    standard_legend = [
        {
            "Data Dictionary Column Name":
            "Field Name",
            "Description":
            "The name of the column in the table or view being referenced in this data dictionary."
        },
        {
            "Data Dictionary Column Name":
            "Description",
            "Description":
            "A brief definition that could stand alone from other element definitions."
        },
        {
            "Data Dictionary Column Name":
            "Reporting Status",
            "Description":
            "Summarizes if the column is being used\nActive = This column is currently being used\nInactive = This column is no longer used"
        },
        {
            "Data Dictionary Column Name":
            "Introduced",
            "Description":
            "The first school year when the column/code was first in use in the database. If unknown, this should be the first date in which the column appears to not be NULL/blanks."
        },
        {
            "Data Dictionary Column Name":
            "Discontinued",
            "Description":
            "The last school year the column/code was used. Assume that if this cell is blank, the column has not been discontinued."
        },
        {
            "Data Dictionary Column Name":
            "Acceptable Values",
            "Description":
            "This column details which values are allowed for a column.\nFormat: cell value = brief description if necessary\nFor columns with many acceptable values, you can use a tab (see testName tab example)"
        },
        {
            "Data Dictionary Column Name":
            "Required?",
            "Description":
            "For use in manually entered fields/tables. Summarizes if the column can be left blank, NULL, or NA.\nR = Required, cannot be left blank\nO = Optional, can be left blank\nC = Conditional, can be left blank depending on other values in the record"
        },
        {
            "Data Dictionary Column Name":
            "Null Meaning",
            "Description":
            "Summarizes the meaning of a NULL value in the column."
            "\nN = NULL values are not allowed by SQL"
            "\nUE = NULL values are allowed by SQL, but are unexpected and should not be in the column"
            "\nDNA = NULL values are allowed by SQL and are expected to be in the column. A NULL value indicates that the field does not apply to the record."
            "\nUNK = NULL values are allowed by SQL and are expected to be in the column. A NULL value indicates that the field is missing or unknown."
            "\nVAL = NULL values are allowed by SQL and are expected to be in the column. A NULL value indicates that the field is valid and has a specific meaning."
            "\nCOND = NULL values are allowed by SQL and are expected to be in the column. A NULL value indicates that the field is conditional on the value of one or more fields."
        },

        # {
        #     "Data Dictionary Column Name": "Valid Nulls",
        #     "Description": "Summarizes if Blank/NULL values that may show up in the field have a valid meaning or interpretation (including if the NULLs just mean that the field is optional) or are the result of an unexpected error."
        #                     "\nY = Yes, Blank/NULL values are valid."
        #                     "\nN = No, Blank/NULL values are not valid."
        # },
        # {
        #     "Data Dictionary Column Name": "Accepts Null?",
        #     "Description": "Summarizes if the column can accept NULL values.\nY = Yes, NULL values are allowed\nN = No, NULL values are not allowed"
        # },
        {
            "Data Dictionary Column Name":
            "Data Type",
            "Description":
            "Details the column's class (string, numeric, date/time, etc.)"
        },
        {
            "Data Dictionary Column Name":
            "Max Characters",
            "Description":
            "The maximum number of characters that this column can hold in a cell"
        },
        {
            "Data Dictionary Column Name":
            "Notes",
            "Description":
            "Any additional historical context or current information about the column that does not apply to other columns in the data dictionary."
        },
        {
            "Data Dictionary Column Name":
            "Validations",
            "Description":
            "List any validations that need to be conducted for that column. A validation is any process, human or machine enforced, that modulates the data to ensure accuracy. Can be left blank if no validations need to be conducted."
        },
        {
            "Data Dictionary Column Name":
            "Key Information",
            "Description":
            "Indicates if the field is a key field for the table.\n"
            " - PK: Primary key\n"
            " - UK: Unique Key\n"
            " - FK: Foreign Key (to a primary or unique key in another table)\n"
            " - EK: Entity Key. Not necessarily unique, but identifies a specific entity in/across the databases."
            " For example, marrsNumber in MARSS.dbo.student is not unique across all records, but it is unique accross all students and therefore identifies a specific student."
            " Do not use if the field is a foreign key. Foreign keys may point to an EK field, however, they should then be labelled 'FE'.\n"
            " - One digit suffix: This suffix should be used to group composite keys (a key consisting of multiple fields). For example if field A and B have key info 'EK1'"
            " and C and D have key info 'EK2', then there are two composite entity keys: {A, B} and {C, D}.\n"
            " - 'S' prefix: This indicates that the key is a proper (has less information) subset of the information stored in a key in another table.\n"
            " - 'M' prefix: This indicates that the key is the master key for that particular field. The table with the master key is what the other table non master keys for that field connect back to.\n"
            "Leave cell blank if this column is not a key field."
        },
        {
            "Data Dictionary Column Name":
            "Source Information",
            "Description":
            "If this column is being populated from another source table, the source database, source table, and source field name are listed here.\nLeave cell blank if this column is not sourced from somewhere else in SQL."
        },
        {
            "Data Dictionary Column Name":
            "Raw Data Origin",
            "Description":
            "The raw data file name (.csv/.xlsx/.tab, etc.) where the data originates.\nLeave cell blank if this column is not directly populated from a raw data file."
        },
        {
            "Data Dictionary Column Name":
            "Reporting Cycle",
            "Description":
            "The cycle in which the data is reported. For example, Fall, End of Year, etc."
        }
    ]
    legend = []
    for column in data_dict_headers:
        for desc in standard_legend:
            if column == desc['Data Dictionary Column Name']:
                legend.append(desc)

    return legend


def standardize_json(data,
                     find_codes=False,
                     order_codes=False,
                     custom_col_names=None,
                     include_web_sleds_info=False):
    '''
    Standardizes the JSON data dictionary by setting the formatting to the standard template.

    Args:
        data (dict): The JSON formatted data dictionary to convert.
        find_codes (bool): Whether or not to populate code sheets with the codes (unique values) that appear in the SQL
        order_codes (bool): Whether or not to sort the code sheets
        custom_col_names (dict): A dictionary of custom column names to use for the workbook (see get_col_headers)
        add_web_sleds_info (bool): Whether or not to add web sleds info

    Returns:
    '''
    name = data['Data Dictionary For']

    server_name, database_name, view_name, table_name = name[1:-1].split('].[')

    # If custom column names are provided, use them
    if custom_col_names:
        data['Workbook Column Names'] = custom_col_names
    else:
        data['Workbook Column Names'] = get_col_headers(database_name)

    # Initialize the code sheet codes
    for variable in tqdm(data['Data Dictionary'],
                         desc=f'Finding code values for {name}',
                         leave=False):
        if 'Acceptable Values' in variable:
            if isinstance(variable['Acceptable Values'], list):
                # This is to check if the variable has character components instead of codes (or non-literal components), in which case we don't want to find codes
                char_components = False
                notes = variable['Notes'].lower()
                if ('character' in notes and 'component' in notes) or (
                        'non' in notes
                        and 'literal' in notes) or ('only' in notes
                                                    and 'special' in notes):
                    char_components = True
                single_find_codes = find_codes if not char_components else False
                current_rows = {
                    row['Code']: row
                    for row in variable['Acceptable Values']
                }

                # Check if 'range' is in the notes or description of the codes, in which case we don't want to find codes
                for code_row in current_rows.values():
                    if 'range' in code_row['Description'].lower(
                    ) or 'range' in code_row['Notes'].lower():
                        single_find_codes = False

                dict_list = initialize_code_sheet(current_rows,
                                                  server_name,
                                                  database_name,
                                                  view_name,
                                                  table_name,
                                                  variable['Field Name'],
                                                  find_codes=single_find_codes,
                                                  order_codes=order_codes)
                variable['Acceptable Values'] = dict_list

    if include_web_sleds_info:
        add_web_sleds_info(data)

    return data


def dd_json_to_excel(data, output_file):
    '''
    Convert a JSON data dictionary to an Excel workbook.

    Args:
        data (dict): The standard format JSON data dictionary to convert.
        output_file (str): The path to the output Excel file to write to.

    Returns:
        None
    '''

    # Create the output directory if it doesn't exist
    directory = os.path.dirname(output_file)
    if directory:
        os.makedirs(directory, exist_ok=True)

    # Initialize a Pandas Excel writer with the xlsxwriter engine
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        workbook = writer.book

        # Define a format for the header
        header_format = workbook.add_format({
            'bold': True,
            'text_wrap': True,
            'valign': 'top',
            'fg_color': '#D9EAD3',  # Light green
            'border': 1
        })

        # Define a text wrap format for general cell content
        text_format = workbook.add_format({
            'text_wrap': True,
            'valign': 'top',
            'num_format': '@'
        })

        # Define a hyperlink format
        hyperlink_format = workbook.add_format({
            'font_color': 'blue',
            'underline': 1,  # 1 for single underline
        })

        bold_format = workbook.add_format({'bold': True})

        # LEGEND SHEET
        # Standard rows for 'Legend' sheet
        column_descriptions = get_legend(
            data['Workbook Column Names']['Data Dictionary'])

        df_column_descriptions = pd.DataFrame(column_descriptions)
        df_column_descriptions.to_excel(writer,
                                        sheet_name='Legend',
                                        index=False,
                                        startrow=1,
                                        header=False)
        worksheet_cd = writer.sheets['Legend']
        # Write the headers with formatting
        for col_num, value in enumerate(df_column_descriptions.columns.values):
            worksheet_cd.write(0, col_num, value, header_format)
            # Set column width to 20
            worksheet_cd.set_column(col_num, col_num, 50, text_format)

        # INFO AND USES SHEET
        df_faqs = pd.DataFrame(data['FAQs'])
        worksheet_info = workbook.add_worksheet('Info and Uses')

        # Write "Data Dictionary For" information
        worksheet_info.write('A1', 'Data Dictionary For:', bold_format)
        worksheet_info.write('A2', data['Data Dictionary For'], text_format)

        # Write "Table Type" information
        worksheet_info.write('A3', f'({data["Table Type"]})', text_format)

        # Write FAQ data starting from the 4th row
        if not df_faqs.empty:
            for idx, (faq, resp) in enumerate(zip(df_faqs['FAQ'],
                                                  df_faqs['Response']),
                                              start=4):
                if pd.isnull(faq):
                    faq = ""
                if pd.isnull(resp):
                    resp = ""
                worksheet_info.write(idx, 0, faq)
                worksheet_info.write(idx, 1, resp)

        # Set column formats for FAQ
        worksheet_info.set_column('A:A', 50, text_format)  # FAQ column width
        # Response column width
        worksheet_info.set_column('B:B', 50, text_format)

        # Format headers for FAQ
        worksheet_info.write('A4', 'FAQ', header_format)
        worksheet_info.write('B4', 'Response', header_format)

        # RELATIONSHIPS SHEET
        df_relationships = pd.DataFrame(data['Relationships'])
        worksheet_relationships = workbook.add_worksheet('Relationships')
        # Write the headers with formatting
        rel_headers = data['Workbook Column Names']['Relationships']
        for col_num, value in enumerate(rel_headers):
            worksheet_relationships.write(0, col_num, value, header_format)
            worksheet_relationships.set_column(col_num, col_num, 50,
                                               text_format)
        # Write the relationship data starting from the second row
        if not df_relationships.empty:
            for idx, row in df_relationships.iterrows():
                for col_num, value in enumerate(row):
                    worksheet_relationships.write(idx + 1, col_num, value)

        # DATA DICTIONARY SHEET
        # Required columns for 'Data Dictionary' sheet
        required_columns = data['Workbook Column Names']['Data Dictionary']
        # Initialize DataFrame for 'Data Dictionary' with required columns
        if 'Data Dictionary' in data:
            df_data_dict = pd.DataFrame(data['Data Dictionary'])
        else:
            df_data_dict = pd.DataFrame(columns=required_columns)

        # Ensure all required columns are present, in the correct order
        df_data_dict = df_data_dict.reindex(columns=required_columns)

        df_data_dict.to_excel(writer,
                              sheet_name='Data Dictionary',
                              index=False,
                              startrow=1,
                              header=False)
        worksheet_ac = writer.sheets['Data Dictionary']
        # Apply text wrap to all cells in the 'Data Dictionary' sheet
        worksheet_ac.set_column('A:Z', None, text_format)
        # Format headers and set column widths
        for col_num, value in enumerate(df_data_dict.columns.values):
            worksheet_ac.write(0, col_num, value, header_format)
        # Setting individual column widths in 'Data Dictionary'
        # Assuming columns: Field Name, Description, Source Information, etc.
        all_column_widths = {
            'Field Name': 25,
            'Description': 50,
            'Source Information': 40,
            'Raw Data Origin': 40,
            'Reporting Status': 15,
            'Introduced': 10,
            'Discontinued': 12,
            'Acceptable Values': 20,
            'Null Meaning': 15,
            'Accepts Null?': 15,
            'Required?': 10,
            'Data Type': 11,
            'Max Characters': 14,
            'Validations': 30,
            'Reporting Cycle': 25,
            'Notes': 50,
            'Key Information': 25,
        }
        # Set individual column widths
        for i, column in enumerate(df_data_dict.columns):
            if column in all_column_widths:
                worksheet_ac.set_column(i, i, all_column_widths[column],
                                        text_format)

        # Codes Sheets
        # For each 'Acceptable Values' that has 'Codes' entry, create a new sheet
        for variable in data['Data Dictionary']:
            if 'Acceptable Values' not in variable or 'Field Name' not in variable:
                continue
            if isinstance(variable['Acceptable Values'], list):
                df_codes = pd.DataFrame(variable['Acceptable Values'])

                # Ensure all required columns are present, in the correct order
                df_codes = df_codes.reindex(
                    columns=data['Workbook Column Names']['Codes'])

                # Truncate the sheet name to 31 characters
                sheet_name = trunc31(variable['Field Name'])
                df_codes.to_excel(writer,
                                  sheet_name=sheet_name,
                                  index=False,
                                  startrow=1,
                                  header=False)
                worksheet_codes = writer.sheets[sheet_name]
                # Apply text wrap to all cells in the new sheet
                worksheet_codes.set_column('A:Z', None, text_format)

                # Replace the 'Acceptable Values' entry with 'Codes'
                # variable['Acceptable Values'] = 'Codes'

                # Format codes sheet headers
                for col_num, value in enumerate(
                        data['Workbook Column Names']['Codes']):
                    worksheet_codes.write(0, col_num, value, header_format)
                    # Set column width to 20
                    worksheet_codes.set_column(col_num, col_num, 20,
                                               text_format)
                # Set the column widths for the codes sheet
                codes_column_widths = {
                    'Code': 15,
                    'Description': 50,
                    'Reporting Status': 15,
                    'Introduced': 12,
                    'Discontinued': 12,
                    'In Data': 7,
                    'Notes': 50
                }
                # Set individual column widths
                for i, column in enumerate(df_codes.columns):
                    if column in codes_column_widths:
                        worksheet_codes.set_column(i, i,
                                                   codes_column_widths[column],
                                                   text_format)

                # Add a hyperlink in the new sheet back to the variable in 'Data Dictionary' sheet
                # Find the row index of the variable in the 'Data Dictionary' sheet
                row_index = df_data_dict[df_data_dict['Field Name'] ==
                                         variable['Field Name']].index[0]
                cell = f'A{row_index + 2}'
                link_target = f"'Data Dictionary'!{cell}"
                formula = f'=HYPERLINK("#{link_target}", "{sheet_name} in Data Dictionary")'
                worksheet_codes.write_formula(
                    f'{chr(65+len(data["Workbook Column Names"]["Codes"]))}1',
                    formula, hyperlink_format)

        # Handling the Acceptable Values column for links
        for idx, row in df_data_dict.iterrows():
            if 'Field Name' not in row or 'Acceptable Values' not in row:
                continue
            if 'Acceptable Values' not in row:
                continue
            if isinstance(row['Acceptable Values'], list):
                # find the column index of 'Acceptable Values'
                col = df_data_dict.columns.get_loc('Acceptable Values')

                # Convert the column index to an Excel column letter
                col_letter = chr(65 + col)

                cell = f'{col_letter}{idx + 2}'
                link_target = f"'{trunc31(row['Field Name'])}'!A1"
                formula = f'=HYPERLINK("#{link_target}", "Codes")'
                worksheet_ac.write_formula(cell, formula, hyperlink_format)


def dd_excel_to_json(input_file, maintain_columns=False):
    """
    Convert a data dictionary Excel file to a JSON string.

    Args:
        input_file (str): The path to the input Excel file.
        maintain_columns (bool): Whether or not to maintain the added/removed columns without reverting
            back to the original column list for that databases

    Returns:
        dict: A formatted JSON dict representing the data dictionary.
    """
    # Define the column names for each sheet
    workbook_column_names = get_col_headers('Typical')

    # Load the dd workbook template
    xl = pd.ExcelFile(input_file)

    # Read the Data Dictionary sheet
    try:
        df_data_dict = xl.parse('Data Dictionary')
    except:
        print(f"Data Dictionary sheet not found in {input_file}")

    if maintain_columns:
        cols = df_data_dict.columns.tolist()
        # Read the column names from the header row and use them as the column names
        workbook_column_names['Data Dictionary'] = cols
        # If Introduced and Discontinued columns are not present, remove them from the code column names
        if 'Introduced' not in cols:
            workbook_column_names['Codes'].remove('Introduced')
        if 'Discontinued' not in workbook_column_names['Data Dictionary']:
            workbook_column_names['Codes'].remove('Discontinued')

    # Read the 'Info and Uses' sheet
    df_info_uses = xl.parse('Info and Uses')

    # Extract the 'Data Dictionary For' information
    # Assuming it's in the second row, first column
    data_dictionary_for = df_info_uses.iloc[0, 0]
    if pd.isnull(data_dictionary_for):
        data_dictionary_for = ""

    # Extract the reference table information
    # Assuming it's in the second row, second column
    table_type = df_info_uses.iloc[1, 0]
    if pd.isnull(table_type):
        table_name = data_dictionary_for.split('.')[-1]
        if 'type' in table_name.lower():
            table_type = "Reference Table"
        else:
            table_type = "Data Table"
    else:
        table_type = table_type.replace('(', '').replace(')', '')

    # Extract the FAQ section
    # Assuming FAQs start from the 4th row and the sheet has headers at the 3rd row
    df_faqs = df_info_uses.iloc[3:].reset_index(drop=True)
    df_faqs = df_faqs.iloc[:, :2]  # Ensure only the first two columns are kept

    # Setting column names
    df_faqs.columns = workbook_column_names['Info and Uses']

    # Convert FAQs to a list of dictionaries
    faq_list = df_faqs.to_dict(orient='records')

    # Initialize a dictionary to hold the final data with additional metadata
    metadata = {
        'Workbook Column Names': workbook_column_names,
        'Legend': [],
        'Data Dictionary For': data_dictionary_for,
        'Table Type': table_type,
        'FAQs': faq_list,
        'Relationships': [],
        'Data Dictionary': []
    }

    # Convert the Legend sheet to a data frame
    try:
        df_descriptions = xl.parse('Legend')
    except:
        print(f"Legend sheet not found in {input_file}")

    # Convert the 'Legend' sheet to a list of dictionaries
    df_descriptions.columns = df_descriptions.columns.str.strip()
    column_descriptions = df_descriptions.to_dict(orient='records')

    # Append the Legend to the data dictionary
    metadata['Legend'] = column_descriptions

    # Relationships sheet
    try:
        # Read the 'Relationships' sheet
        df_relationships = xl.parse('Relationships')

        # Convert the 'Relationships' sheet to a list of dictionaries
        df_relationships.columns = df_relationships.columns.str.strip()
        relationships = df_relationships.to_dict(orient='records')

        # Append the relationships to the data dictionary
        metadata['Relationships'] = relationships
    except:
        metadata['Relationships'] = []

    # Strip the leading/trailing whitespace and remove all \n from the keys
    df_data_dict.columns = df_data_dict.columns.str.strip()

    # Iterate over each row in the 'Data Dictionary' DataFrame
    for index, row in df_data_dict.iterrows():
        record = row.to_dict()

        # Change all empty cells to "" and strip any leading/trailing whitespace.
        for key, value in record.items():
            if pd.isnull(value):
                record[key] = ""
            elif isinstance(value, str):
                record[key] = value.strip()

        # Check if the 'Acceptable Values' indicates there are codes to be read from another sheet
        if record['Acceptable Values'] == 'Codes' or record[
                'Acceptable Values'] == 0:
            column_name = record['Field Name'].strip()

            # Read the specific sheet for the codes, assuming it is named exactly as the 'Field Name'
            if column_name in xl.sheet_names:
                df_codes = xl.parse(column_name, dtype=str)

                # Strip the leading/trailing whitespace and remove all \n from the keys
                # df_codes.columns = df_codes.columns.str.strip(
                # ).str.replace('\n', '')

                # Convert the codes sheet into a list of dictionaries
                codes_list = df_codes.to_dict(orient='records')

                # Change all empty cells to "NULL" and strip any leading/trailing whitespace. Remove all \n
                for code in codes_list:
                    for key, value in code.items():
                        if pd.isnull(value):
                            if key == 'Code':
                                code[key] = "NULL"
                            else:
                                code[key] = ""
                        elif isinstance(value, str):
                            code[key] = value.strip()

                # Replace the 'Acceptable Values' entry with this list
                record['Acceptable Values'] = codes_list
            else:
                record['Acceptable Values'] = []

        # Append the modified record to the data dictionary list
        metadata['Data Dictionary'].append(record)

    return metadata


def standardize_excel(input_file,
                      output_file,
                      make_json=False,
                      find_codes=False,
                      order_codes=False,
                      maintain_columns=False,
                      custom_col_names=None,
                      include_web_sleds_info=False):
    """
    Standardizes and updates the Excel file for the data dictionary by setting the formatting to 
    the standard template.

    Args:
        input_file (str): The path to the input Excel file.
        output_file (str): The path to the output Excel file.
        make_json (bool): Whether or not to write the intermediary json to a file. This will be identical to the output file with the .json extension instead of .xlsx.
        find_codes (bool): Whether or not to populate code sheets with the codes (unique values) that appear in the SQL
        order_codes (bool): Whether or not to sort the code sheets
        maintain_columns (bool): Whether or not to maintain the columns from the original Excel file
        custom_col_names (dict): A dictionary of custom column names to use for the workbook (see get_col_headers)
        add_web_sleds_info (bool): Whether or not to add web sleds info

    Returns:
        None
    """
    # Convert Excel to JSON
    json_output = dd_excel_to_json(input_file,
                                   maintain_columns=maintain_columns)

    # Standardize the JSON
    standard_json = standardize_json(
        json_output,
        find_codes=find_codes,
        order_codes=order_codes,
        custom_col_names=custom_col_names,
        include_web_sleds_info=include_web_sleds_info)

    # Create a JSON file if requested
    if make_json:
        with open(output_file.replace('.xlsx', '.json'), 'w') as f:
            f.write(json.dumps(standard_json, indent=4))

    dd_json_to_excel(standard_json, output_file)


def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [
        str(file) for file in path.rglob(f'*{extension}') if file.is_file()
    ]


# main
if __name__ == "__main__":
    file = "data\EDU-SQLPROD01\DIRS\dbo\DIRS.dbo.AltEdServicesType_data_dict.xlsx"
    standardize_excel(file,
                      file.replace('dbo', 'dbo2'),
                      make_json=False,
                      find_codes=False,
                      order_codes=False,
                      maintain_columns=True)
