import json
import os


def initialize_web_sleds_code_fields(data_dict):
    """
    Initializes the acceptable value fields in the data dict to be empty lists if they are not already and there are web SLEDS codes

    Args:
        data_dict (dict): The json formatted data dictionary to add web SLEDS info to.

    Returns:
        dict: The updated data dictionary with web SLEDS info added.
    """
    dd_for = data_dict["Data Dictionary For"]
    dd_for_list = dd_for[1:-1].split("].[")
    table = dd_for_list[3].lower()
    with open("fetched_data.json", "r") as f:
        fetched_data = json.load(f)

    # Ensure the table is in the web SLEDS data
    if table not in fetched_data:
        return data_dict

    for field in data_dict["Data Dictionary"]:
        if field["Acceptable Values"] == "":
            field["Acceptable Values"] = []
    return data_dict


def add_web_sleds_info(data_dict):
    """
    Add web SLEDS info to the data dictionary

    Args:
        data_dict (dict): The json formatted data dictionary to add web SLEDS info to.

    Returns:
        dict: The updated data dictionary with web SLEDS info added.
    """
    fetched_data_path = os.path.join(os.path.dirname(__file__), "fetched_data.json")
    with open(fetched_data_path, "r") as f:
        fetched_data = json.load(f)

    dd_for = data_dict["Data Dictionary For"]
    dd_for_list = dd_for[1:-1].split("].[")
    table = dd_for_list[3].lower()
    if table not in fetched_data:
        return data_dict
    fetched_data_dict = fetched_data[table]

    for field in data_dict["Data Dictionary"]:
        field_name = field["Field Name"].lower()

        if field_name in fetched_data_dict:
            if field["Description"] == "":
                field["Description"] = fetched_data_dict[field_name]["description"]

            if fetched_data_dict[field_name]["number_of_codes"] != "":
                if (
                    type(field["Acceptable Values"]) == str
                ):  # Convert to code list if no codes yet
                    field["Acceptable Values"] = []

                # Initialize notes
                for code_data in field["Acceptable Values"]:
                    # Notes reflect whether or not the code is present in the database and web SLEDS
                    if (
                        "(In database but not in web SLEDs data dictionary)"
                        not in code_data["Notes"]
                    ):
                        code_data["Notes"] = (
                            "(In database but not in web SLEDs data dictionary) "
                            + code_data["Notes"]
                        )

                for web_code_data in fetched_data_dict[field_name]["codes"]:
                    present = False  # Indicator of if the code is already present
                    web_code = (
                        "Blank"
                        if web_code_data["code"] == ""
                        else web_code_data["code"]
                    )  # Handle blank codes

                    for code_data in field["Acceptable Values"]:

                        if (
                            code_data["Code"].lower() == web_code.lower()
                        ):  # _data['code']:
                            present = True
                            if (
                                code_data["Description"] == ""
                            ):  # Update description to the web description
                                new_description = web_code_data["longDefinition"]
                                if new_description == "":
                                    new_description = web_code_data["definition"]
                                code_data["Description"] = new_description
                                code_data["Notes"] = code_data["Notes"].replace(
                                    "(In database but not in web SLEDs data dictionary)",
                                    "(In web SLEDs data dictionary and database)",
                                )
                            break
                    # If the code is not present, add it
                    if not present:
                        field["Acceptable Values"].append(
                            {
                                "Code": web_code,
                                "Description": (
                                    web_code_data["longDefinition"]
                                    if web_code_data["longDefinition"] != ""
                                    else web_code_data["definition"]
                                ),
                                "In Data": "N",
                                "Notes": "(In web SLEDs data dictionary but not in database)",
                            }
                        )

    return data_dict
