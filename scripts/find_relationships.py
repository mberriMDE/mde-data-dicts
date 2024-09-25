import json
import csv
from collections import defaultdict
from pathlib import Path
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import networkx as nx
import pygraphviz as pgv
import re
import urllib.parse

# class KeyField:

#     def __init__(self, global_name: str, local_name: str):
#         self.global_name = global_name
#         self.local_name = local_name


class Key:
    '''
    A class to represent a key in a table.
    Attributes:
        keys (frozenset[tuple]): The set of fields that compose the key. Each field is a tuple of the global name (index 0) and local name (index 1).
        type (str): The type of key (PK, UK, EK, FK, FE).
            PK = Primary Key
            UK = Unique Key
            EK = Entity Key
            FK = Foreign Key
            FE = Foreign Entity Key
        master_type (str): The type of master key, Local (L) or Regular (M). None if the key is not a master key.
            Local master keys only have relationships within the same database. Regular master keys can have relationships across databases.
            If a local and regular master key have the same global name, then the local master key will be used, but an edge will be drawn
            from the local to the regular master key.
        dd_for (str): The table that the key is for
        equivalent_key_set (frozenset[KeyField]): The set of keys that are equivalent to this key
        subset_of (frozenset[KeyField]): The set of keys that this key contains a subset of information from. 
            This should be the set of keys that this key maps to, not the equivalent keys.


    '''

    def __init__(self,
                 key_set: frozenset[tuple],
                 type: str,
                 master_type: str,
                 dd_for: str,
                 equivalent_key_set: frozenset[tuple] = None,
                 subset_of: frozenset[tuple] = None):
        self.keys = key_set
        self.type = type
        self.master_type = master_type
        self.dd_for = dd_for
        self.equivalent_key_set = equivalent_key_set
        self.subset_of = subset_of

        self.global_names = frozenset([g[0] for g in key_set])
        self.local_names = frozenset([l[1] for l in key_set])

        # If there is more than one key, then the label should be a set of the key names
        if len(self.global_names) > 1:
            self.global_label = '{' + ', '.join(self.global_names) + '}'
            self.local_label = '{' + ', '.join(self.local_names) + '}'
        else:
            self.global_label = next(iter(self.global_names))
            self.local_label = next(iter(self.local_names))

        # self.dict = {self.global_name: key for key in key_set}

    def __str__(self):
        display = f'{self.global_label}:'
        if self.master_type == 'L':
            display += f' Local Master {self.type}'
        elif self.master_type == 'M':
            display += f' Master {self.type}'
        else:
            display += f' {self.type}'
        display += f', in ({self.dd_for})'

        if self.subset_of is not None:
            display += f', (subset of {self.subset_of})'

        if self.equivalent_key_set is not None:
            display += f', (equivalent to {self.equivalent_key_set})'

        return display


class TableNode:

    def __init__(self,
                 subgraph,
                 dd_for,
                 table_type,
                 keys=[],
                 url=None,
                 **attr):
        self.subgraph = subgraph
        self.dd_for = dd_for
        self.table_type = table_type
        self.keys = keys
        self.attr = attr

        # Table naming convention: [server].[database].[view].[table]
        names = dd_for[1:-1].split('].[')  # Convert bracketed names to list
        self.server = names[0]
        self.database = names[1]
        self.view = names[2]
        self.table = names[3]

        # Set the url to the SharePoint page for the table if not provided
        '''
        URL Example:
        https://mn365.sharepoint.com/:x:/r/teams/MDE/DataDictionaries/Shared%20Documents/SQLPROD01/MDEORG/apicurrent/MDEORG.apicurrent.AddressType_data_dict.xlsx?web=1
        '''
        if url is None:
            url = f'https://mn365.sharepoint.com/:x:/r/teams/MDE/DataDictionaries/Shared%20Documents/{self.server}/{self.database}/{self.view}/{self.database}.{self.view}.{self.table}_data_dict.xlsx?web=1'
        # url = "https://mn365.sharepoint.com/:x:/r/teams/MDE/DataDictionaries/Shared%20Documents/EDU-SQLPROD01/MDEORG/apicurrent/MDEORG.apicurrent.AddressType_data_dict.xlsx?web=1"
        encoded_url = urllib.parse.quote(url, safe='/:?&=%.')
        self.url = encoded_url

        # Create the node in the graph
        self.subgraph.add_node(dd_for, **self.attr)
        self.node = self.subgraph.get_node(dd_for)

        # Set node attributes
        self.node.attr['style'] = 'filled'
        self.node.attr['color'] = 'black'
        self.node.attr['shape'] = 'circle'
        self.node.attr['fillcolor'] = self.subgraph.node_attr['fillcolor']
        self.node.attr['label'] = ''
        self.node.attr['tooltip'] = f'{self.view}.{self.table}'
        self.node.attr['URL'] = self.url

    def add_key(self, key):
        self.keys.append(key)

    def set_url(self, url):
        self.url = url
        self.subgraph.get_node(self.dd_for).attr['URL'] = url


class TableEdge:

    def __init__(self, graph: pgv.AGraph, source: 'TableNode',
                 target: 'TableNode', source_key, target_key, **attr):
        self.graph = graph
        self.source = source
        self.target = target
        self.source_key = source_key
        self.target_key = target_key
        self.attr = attr

        # Automatically calculate same_view, same_database, and same_server
        self.same_server = source.server == target.server
        self.same_database = self.same_server and source.database == target.database
        self.same_view = self.same_database and source.view == target.view

        # Create the edge in the graph
        self.graph.add_edge(graph.get_node(source.dd_for),
                            graph.get_node(target.dd_for),
                            dir="back",
                            **self.attr)
        self.edge = self.graph.get_edge(source.dd_for, target.dd_for)

        tooltip = f'{source.dd_for}.[{source_key.local_label}]\n <- {target.dd_for}.[{target_key.local_label}]'
        # Set edge attributes based on metadata
        # self.graph.get_edge(
        #     source.dd_for,
        #     target.dd_for).attr['label'] = source_key.global_name
        # self.graph.get_edge(
        #     source.dd_for, target.dd_for
        # ).attr['color'] = 'blue' if self.same_server else 'red'
        # self.graph.get_edge(
        #     source.dd_for, target.dd_for
        # ).attr['style'] = 'solid' if self.same_database else 'dashed'
        # self.graph.get_edge(source.dd_for,
        #                     target.dd_for).attr['tooltip'] = tooltip
        self.edge.attr['color'] = 'blue' if self.same_database else self.edge[
            0].attr['fillcolor']
        self.edge.attr['style'] = 'solid' if self.same_database else 'dashed'
        self.edge.attr['tooltip'] = tooltip


# List all excel files in a given directory
def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [
        str(file) for file in path.rglob(f'*{extension}') if file.is_file()
    ]


# Load the data dictionary information from the excel files
def load_json_data(file_paths):
    data = []
    for file_path in file_paths:
        if 'data_dict' not in file_path:
            continue
        json_str = dd_excel_to_json(file_path)
        data_dict = json.loads(json_str)
        data.append(data_dict)
    return data


# Group the data dictionary information by database
def format_json_data(raw_data):
    formatted_data = {}
    for dd in raw_data:
        dd_for = dd['Data Dictionary For']
        # Table naming convention: [server].[database].[view].[table]
        names = dd_for[1:-1].split('].[')  # Convert bracketed names to list
        server = names[0]
        database = names[1]
        view = names[2]
        table = names[3]
        if database not in formatted_data:
            formatted_data[database] = []
        formatted_data[database].append(dd)

    return formatted_data


# Generate a list of colors
def generate_colors():
    colors = [
        "lightpink",
        "lightgoldenrod",
        "palegreen",
        "coral",
        "orchid1",
        "lightsalmon",
        "plum",
        "seashell3",
        "mistyrose",
        "lavender",
    ]
    return colors


def find_code_population_origins(json_data):
    '''
    Search the data dictionaries for origin fields for populating code sheets
    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information

    Returns:
        population_map_origins (defaultdict(lambda: (None, []))): A dictionary mapping global field names to a tuple containing the origin
            tables (identified by the 'Data Dictionary For' value) for that field's codes (index 0) and a list of the destination tables (index 1). The function will return an empty list
            of destination nodes and only fill the origin nodes.
    '''

    population_map_origins = defaultdict(lambda: (None, []))
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        for field in data_dict['Data Dictionary']:
            info_list = field['Key Information'].split(',')
            global_name = None
            pop_string = None
            for info in info_list:
                info = info.strip()
                if info.startswith('G:'):
                    global_name = info.split(':')[1].strip()
                elif len(info) == 1:
                    pop_string = info
            if global_name is None:
                # Default to the field name if no global name is specified
                global_name = field['Field Name']
            if pop_string == 'O':
                population_map_origins[global_name] = (dd_for, [])

    return population_map_origins


def fill_Ds(json_data, population_map_origins, print_changes=False):
    '''
    Fill in destination fields for populating code sheets

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        population_map_origins (defaultdict(lambda: (None, []))): A dictionary mapping global field names to a tuple containing the origin
            node for that field's codes (index 0) and an empty list of the destination nodes (index 1).

    Returns:
        json_data (list[dict]): List of dictionaries containing data dictionary information.
    '''
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        for item in data_dict['Data Dictionary']:
            info_list = item['Key Information'].split(',')
            info_list = [i.strip() for i in info_list]
            local_name = item['Field Name']
            global_name = next((g for g in population_map_origins
                                if g.lower() == local_name.lower()), None)
            if global_name is not None:
                if 'D' not in info_list and 'O' not in info_list:
                    info_list.append('D')
                item['Key Information'] = ', '.join(info_list)
                if print_changes:
                    print(f"{dd_for}.[{local_name}] <- D")

    return json_data


def add_code_population_destinations(json_data, population_map_origins):
    '''
    Add destination fields for populating code sheets

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        population_map_origins (defaultdict(lambda: (None, []))): A dictionary mapping global field names to a tuple containing the origin
            node for that field's codes (index 0) and an empty list of the destination nodes (index 1).

    Returns:
        population_map (defaultdict(lambda: (None, []))): A dictionary mapping global field names to a tuple containing the origin
            node for that field's codes (index 0) and a list of the destination nodes (index 1).
    '''
    population_map = population_map_origins
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        for item in data_dict['Data Dictionary']:
            info_list = item['Key Information'].split(',')
            global_name = None
            pop_string = None
            for info in info_list:
                info = info.strip()
                if info.startswith('G:'):
                    global_name = info.split(':')[1].strip()
                elif len(info) == 1:
                    pop_string = info
            if global_name is None:
                # Default to the first global name in population_map that is the same as the field name (case insensitive)
                global_name = next(
                    (g for g in population_map
                     if g.lower() == item['Field Name'].lower()), None)
            if pop_string == 'D':
                if global_name is None:
                    print(
                        f"Error in {dd_for}.[{item['Field Name']}]: Global name {global_name} has no code origin"
                    )
                    continue
                population_map[global_name][1].append(dd_for)

    return population_map


def find_master_keys(json_data, equivalent_keys=None):
    '''
    Search the data dictionaries in json data for master keys.

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        equivalent_keys (dict): Maps a master key field to a list of fields that form a composite key of equivalent information

    Returns:
        key_dict_masters (defaultdict(lambda: defaultdict(lambda: (None, [])))): Dictionary containing the (master) keys information. The outer dict key is 
            the global name of a shared key. The value is the inner dictionary. The 'Default' dictionary key
            in the inner dictionary stores the regular master key for a particular global name. The remaining inner dictionary keys 
            store local master keys with the relevant database being the inner dictionary key. The inner dictionary values are tuples of 
            the master key and a list of the child keys. 
            example:
            {
                'global_name1': {
                                    'Default': (master_key, [])
                                    'server1.database1': (local_master_key, [])
                                }
            }
            Note that this function returns only empty lists of child keys.

    '''
    key_dict_masters = defaultdict(lambda: defaultdict(lambda: (None, [])))
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        server = dd_for[1:-1].split('].[')[0]
        database = dd_for[1:-1].split('].[')[1]
        for item in data_dict['Data Dictionary']:
            info_list = item['Key Information'].split(',')
            info_list = [i.strip() for i in info_list]
            local_name = item['Field Name']
            keystring = None
            global_name = None
            for info in info_list:
                re_str = r"^[ML][PUE]K$"
                if re.match(re_str, info):
                    keystring = info
                elif info.startswith('G:'):
                    global_name = info.split(':')[1].strip()

            if keystring is None:
                # Skip non-master keys
                continue

            if global_name is None:
                # Default to the field name if no global name is specified
                global_name = local_name

            key_set = frozenset([(global_name, local_name)])
            key_type = keystring[1:2]
            master_type = keystring[0:1]
            equivalent_key_set = next(
                (frozenset(equivalent_keys[k])
                 for k in equivalent_keys if k.lower() == global_name.lower()),
                None)
            key = Key(key_set, key_type, master_type, dd_for,
                      equivalent_key_set)

            if master_type == 'M':
                key_dict_masters[global_name]['Default'] = (key, [])
            elif master_type == 'L':
                key_dict_masters[global_name][server + '.' + database] = (key,
                                                                          [])

    return key_dict_masters


def fill_keys(json_data,
              key_dict_masters,
              generate_excel=True,
              equivalent_keys=None):
    '''
    Fill in missing foreign keys in the data dictionary information.

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        key_dict_masters (defaultdict(lambda: defaultdict(lambda: (None, []))): Dictionary containing only the master keys information.
        generate_excel (bool): If True, generate new excel files with filled in foreign keys and composite keys 
        equivalent keys (dict): Maps a master key field to a list of fields that form a composite key of equivalent information
    
    Returns:
        json_data (list[dict]): List of dictionaries containing data dictionary information with filled in foreign keys.

        key_dict (defaultdict(lambda: defaultdict(lambda: (None, []))): Dictionary containing the keys information.The outer dict key is 
            the global name of a shared key. The value is the inner dictionary. The 'Default' dictionary key
            in the inner dictionary stores the regular master key for a particular global name. The remaining inner dictionary keys 
            store local master keys with the relevant database being the inner dictionary key. The inner dictionary values are tuples of 
            the master key and a list of the child keys. 
            example:
            {
                'global_name1': {
                                    'Default': (master_key, [child_key1, child_key2])
                                    'server1': (local_master_key, [child_key1, child_key2])
                                }
            }
    '''

    # # equivalence map stores the equivalent keys for each key
    # equivalence_map = {}
    # for global_names, key in master_keys:
    #     if key.equivalent_key_set:
    #         for equivalent_key in key.equivalent_key_set:
    #             equivalence_map[equivalent_key] = key

    # Fill in missing foreign keys and add them to key_dict
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        database = dd_for.split('].[')[1]
        for variable in data_dict['Data Dictionary']:
            # key_info = variable['Key Information']
            key_infos = variable['Key Information'].split(',')
            write_to_key_infos = []
            col_name = variable['Field Name']
            for key_info in key_infos:
                if len(key_info) > 0:
                    if key_info[0] == 'M' or key_info[
                            0] == 'L':  # Skip master/local master keys
                        write_to_key_infos.append(key_info)
                        continue
                    if key_info[0] == 'S':  # Skip subset keys
                        write_to_key_infos.append(key_info)
                        continue
                    if key_info[-1] in [
                            '1', '2', '3', '4', '5', '6', '7', '8', '9', '0'
                    ]:  # Skip composite keys
                        write_to_key_infos.append(key_info)
                        continue
                if ':' not in key_info:  # Identical global name
                    # This statement finds the global name of the first key (with key_set length 1) that matches the column name
                    match = next(
                        (global_names
                         for global_names in key_dict_masters.keys()
                         if len(global_names) == 1 and next(iter(
                             global_names)).lower() == col_name.lower()), None)
                    if match:
                        if database in key_dict_masters[match]:
                            use_db = database
                        else:
                            use_db = 'Default'
                        master_key = key_dict_masters[match][use_db][0]

                        if master_key.type == 'PK' or master_key.type == 'UK':
                            write_to_key_infos.append('FK')

                            # Add the identified key to the key_dict
                            key_dict_masters[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FK',
                                    None, dd_for))

                        elif master_key.type == 'EK':
                            write_to_key_infos.append('FE')

                            # Add the identified key to the key_dict
                            key_dict_masters[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FE',
                                    None, dd_for))
                else:
                    global_name = key_info.split(':')[1].strip()
                    match = next(
                        (global_names
                         for global_names in key_dict_masters.keys()
                         if len(global_names) == 1 and next(iter(
                             global_names)).lower() == col_name.lower()), None)

                    if match:
                        if database in key_dict_masters[match]:
                            use_db = database
                        else:
                            use_db = 'Default'
                        master_key = key_dict_masters[match][use_db][0]

                        if master_key.type == 'PK' or master_key.type == 'UK':
                            write_to_key_infos.append('FK: ' + global_name)

                            # Add the identified key to the key_dict
                            key_dict_masters[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FK',
                                    None, dd_for))
                        elif master_key.type == 'EK':
                            variable['Key Information'] = 'FE: ' + global_name

                            # Add the identified key to the key_dict
                            key_dict_masters[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FE',
                                    None, dd_for))

    # Fill in missing composite keys
    for data_dict in json_data:
        # Get a set of all the fields in the data dictionary
        fields = set()

        # Dictionary to hold the composite keys that are present in the data dictionary along with the composite suffix (count)
        present_comp_keys = defaultdict(set)
        count = 1
        for variable in data_dict['Data Dictionary']:
            fields.add(variable['Field Name'])
            # Add the global names if they exist
            key_infos = variable['Key Information'].split(',')
            for key_info in key_infos:
                if len(key_info) > 0:
                    if key_info[0] in ['M', 'L', 'S']:
                        # Skip master/local master keys and subset keys
                        continue
                splut = variable['Key Information'].split(':')
                if len(splut) > 1:
                    fields.add(splut[1].strip())
        lower_fields = set(subkey.lower() for subkey in fields)

        for mck_names in key_dict_masters.keys():
            if len(mck_names) == 1:  # Skip single keys
                continue
            lower_mck_names = set(c.lower() for c in mck_names)
            if lower_mck_names.issubset(lower_fields):
                present_comp_keys[mck_names] = count
                count += 1
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            server = data_dict['Data Dictionary For'].split('].[')[0]
            col_name = variable['Field Name']
            if len(key_info) > 0:
                if key_info[0] in ['M', 'L', 'S']:
                    continue
            if key_info == '' or ':' not in key_info:  # Check if the local name is in the composite key
                for comp_key_names in present_comp_keys:
                    comp_key_names_lower = set(c.lower()
                                               for c in comp_key_names)
                    if col_name.lower() in comp_key_names_lower:
                        if server in key_dict_masters[comp_key_names]:
                            use_db = server
                        else:
                            use_db = 'Default'
                        mck = key_dict_masters[comp_key_names][use_db][0]
                        if mck.type == 'PK' or key_dict_masters[
                                comp_key_names] == 'UK':
                            variable[
                                'Key Information'] = f'FK{present_comp_keys[comp_key_names]}'
                        elif mck.type == 'EK':
                            variable[
                                'Key Information'] = f'EK{present_comp_keys[comp_key_names]}'
            if ':' in key_info:  # Check if the global name is in the composite key
                global_name = key_info.split(':')[1].strip()
                for comp_key_names in present_comp_keys:
                    comp_key_names_lower = set(c.lower()
                                               for c in comp_key_names)
                    if global_name.lower() in comp_key_names_lower:
                        if key_dict_masters[
                                comp_key_names].type == 'PK' or key_dict_masters[
                                    comp_key_names] == 'UK':
                            variable[
                                'Key Information'] = f'FK{present_comp_keys[comp_key_names]}'


#     master_keys.update(master_comp_keys)

#     if generate_excel:
#         for data_dict in json_data:
#             dd_for = data_dict['Data Dictionary For']
#             names = dd_for[1:-1].split('].[')
#             server = names[0]
#             database = names[1]
#             view = names[2]
#             table = names[3]
#             dd_json_to_excel(
#                 json.dumps(data_dict, indent=4),
#                 f'filled\\{server}\\{database}\\{view}\\{database}.{view}.{table}_data_dict.xlsx'
#             )

#     return json_data, master_keys


def build_graph(json_data, draw_path, show_reference_tables=True):
    '''
    Args:
        json_data (list of dict): List of dictionaries containing data dictionary information
        draw_path (str): Path to save the graph image

    Returns:
        G (pgv.AGraph): Graph object containing the data dictionary relationships

    If the global name of the key is different than the field name, 
    start by mapping PKs and UKs to FKs in external tables. PKs and UKs should map to PKs, UKs of the same
    name in external tables
    '''
    # Fill in missing foreign keys
    json_data, master_keys = fill_keys(json_data)
    return None


if __name__ == "__main__":
    if not Path('results').exists():
        Path('results').mkdir()

    directories = [
        'data\\excel_dds\\EDU-SQLPROD01\\MDEORG',
        'data\\excel_dds\\EDU-SQLPROD01\\MARSS',
        'data\\excel_dds\\EDU-SQLPROD01\\DIRS',
        'data\\excel_dds\\EDU-SQLPROD01\\EDMCourseCatalog',
        'data\\excel_dds\\EDU-SQLPROD01\\ESSA',
        'data\\excel_dds\\EDU-SQLPROD01\\Assessments'
    ]
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    json_data = load_json_data(files)

    with open('data\\equivalent_fields.json', 'r') as f:
        equivalent_keys = json.load(f)
    key_dict_masters = find_master_keys(json_data, equivalent_keys)

    print(key_dict_masters)

    # origins = find_code_population_origins(json_data)
    # for name, (origin, dests) in origins.items():
    #     print(f'{name}: {origin} -> {dests}')
    # filled_json_data = fill_Ds(json_data, origins, print_changes=True)
    # population_map = add_code_population_destinations(filled_json_data,
    #                                                   origins)
    # for name, (origin, dests) in population_map.items():
    #     print(f'{name}: {origin} -> {dests}')

    # G = build_graph(json_data,
    #                 'results\\subkeys.svg',
    #                 show_reference_tables=True)

    # json_data, master_keys = fill_keys(json_data)
