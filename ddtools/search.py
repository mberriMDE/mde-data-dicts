from .json_excel_conversion import *


def search_data_dicts(directories: list[str],
                      search_terms: list[str],
                      column_names: list[str] = ["Field Names"],
                      search_term_op: str = "AND",
                      column_op: str = "OR",
                      match_case: bool = False,
                      concat: bool = False) -> list:
    """
    Args:
        directories (list[str]): A list of directories to search for data dictionary files.
        search_terms (list): A list of search terms to search for in the data dictionary files.
        column_names (list, optional): A list of column names to search for the search terms. Defaults to ["Field Names"].
        search_term_op (str, optional): The operation to perform on the search terms. Defaults to "AND".
        column_op (str, optional): The operation to perform on the columns. Defaults to "OR".
        match_case (bool, optional): Whether or not to match the case of the search terms. Defaults to False.
        concat (bool, optional): Whether or not to concatenate the columns before searching. Defaults to False.

    Returns:
        list: A list of the locations of the search terms in the data dictionary files.
    """
    files = []
    for d in directories:
        files.extend(list_files(d))
    # for file in files:
    #     if "_data_dict.xlsx" not in file:
    #         files.remove(file)
    match_locations = []
    for file in files:
        if "_data_dict.xlsx" not in file:
            continue
        # print(file)
        json_data = dd_excel_to_json(file)
        dd_for = json_data["Data Dictionary For"]

        for item in json_data["Data Dictionary"]:
            if concat:
                col_vals = [item[col] for col in column_names]
                concat_vals = " ".join(col_vals)
                if search_term_op == "AND":  # Every search term must be in the field
                    if not match_case:
                        if not all(term.lower() in concat_vals.lower()
                                   for term in search_terms):
                            continue
                    else:
                        if not all(term in concat_vals
                                   for term in search_terms):
                            continue

                if search_term_op == "OR":  # At least one search term must be in the field
                    if not match_case:
                        if not any(term.lower() in concat_vals.lower()
                                   for term in search_terms):
                            continue
                    else:
                        if not any(term in concat_vals
                                   for term in search_terms):
                            continue

                location = f"{dd_for}.[{item['Field Name']}]"
                match_locations.append(location)

            elif not concat:
                if column_op == "AND":  # Search critera must be met in every column in column_names
                    in_all = True
                    for col in column_names:
                        if search_term_op == "AND":  # All search terms must be in the field
                            if not match_case:
                                if not all(term.lower() in item[col].lower()
                                           for term in search_terms):
                                    in_all = False
                                    break
                            else:
                                if not all(term in item[col]
                                           for term in search_terms):
                                    in_all = False
                                    break
                        elif search_term_op == "OR":  # At least one search term must be in the field
                            if not match_case:
                                if not any(term.lower() in item[col].lower()
                                           for term in search_terms):
                                    in_all = False
                                    break
                            else:
                                if not any(term in item[col]
                                           for term in search_terms):
                                    in_all = False
                                    break
                    if in_all:
                        location = f"{dd_for}.[{item['Field Name']}]"
                        match_locations.append(location)

                if column_op == "OR":  # Search critera must be met in at least one column in column_names
                    in_any = False
                    for col in column_names:
                        if search_term_op == "AND":  # All search terms must be in the field
                            if not match_case:
                                if all(term.lower() in item[col].lower()
                                       for term in search_terms):
                                    in_any = True
                                    break
                            else:
                                if all(term in item[col]
                                       for term in search_terms):
                                    in_any = True
                                    break
                        elif search_term_op == "OR":  # At least one search term must be in the field
                            if not match_case:
                                if any(term.lower() in item[col].lower()
                                       for term in search_terms):
                                    in_any = True
                                    break
                            else:
                                if any(term in item[col]
                                       for term in search_terms):
                                    in_any = True
                                    break
                    if in_any:
                        location = f"{dd_for}.[{item['Field Name']}]"
                        if len(column_names) > 1:
                            location += f" ({col})"
                        match_locations.append(location)

    return match_locations


if __name__ == "__main__":
    directories = ['data\\excel_dds\\EDU-SQLPROD01\\MDEORG']
    search_terms = ['program']
    column_names = ['Field Name']
    match_locations = search_data_dicts(directories,
                                        search_terms,
                                        column_names,
                                        search_term_op="AND",
                                        column_op="OR",
                                        match_case=False,
                                        concat=False)
    for location in match_locations:
        print(location)

    # directories = ['data\\excel_dds\\EDU-SQLPROD01']
    # search_terms = ['statusendcode']
    # column_names = ['Description']
    # match_locations = search_data_dicts(directories,
    #                                     search_terms,
    #                                     column_names,
    #                                     search_term_op="OR",
    #                                     column_op="OR",
    #                                     match_case=False)
    # for location in match_locations:
    #     print(location)
