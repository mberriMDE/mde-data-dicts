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


# class Key:

#     def __init__(self, global_name: str, local_name: str, type: str,
#                  is_master: bool, dd_for: str):
#         self.global_name = global_name
#         self.local_name = local_name
#         self.global_label = global_name
#         self.local_label = local_name
#         self.type = type
#         self.is_master = is_master
#         self.dd_for = dd_for

# class CompositeKey:

#     def __init__(self, key_set: frozenset[Key], type: str, is_master: bool,
#                  dd_for: str):
#         self.keys = key_set
#         self.global_names = frozenset([g.global_name for g in key_set])
#         self.local_names = frozenset([l.local_name for l in key_set])
#         self.global_label = '{' + ', '.join(self.global_names) + '}'
#         self.local_label = '{' + ', '.join(self.local_names) + '}'
#         self.type = type
#         self.is_master = is_master
#         self.dd_for = dd_for
#         self.dict = {key.global_name: key for key in key_set}


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


def fill_keys(json_data, generate_excel=True, equivalent_keys=None):
    '''
    Fill in missing foreign keys in the data dictionary information.

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        generate_excel (bool): If True, generate new excel files with filled in foreign keys and composite keys 
    
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
    # Dictionary to hold all master keys with their types and tables
    key_dict = defaultdict(lambda: defaultdict(lambda: (None, [])))
    for data_dict in json_data:
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            if key_info == '':
                continue
            re_str = r"[ML][PUE]K\d?"
            search_obj = re.search(re_str, key_info)
            if search_obj:
                match = search_obj.group()
                if re.search(r"\d", match) is not None:
                    continue  # Skip composite keys
                master_type = match[0]
                key_type = match[1:3]
            else:
                continue
            '''
            If the key information has a colon and a space, then the key maps to a different key name.
            The global name is the key name that the key maps to.
            '''
            if ':' in variable['Key Information']:
                global_name = variable['Key Information'].split(':')[1].strip()
            else:
                global_name = variable['Field Name']
            equivalent_key_set = None
            if equivalent_keys:
                if global_name in equivalent_keys:
                    equivalent_key_set = frozenset(
                        equivalent_keys[global_name])
            mk = Key(frozenset([(global_name, variable['Field Name'])]),
                     key_type,
                     master_type,
                     data_dict['Data Dictionary For'],
                     equivalent_key_set=equivalent_key_set
                     )  # Master Keys cannot be proper subsets of other keys
            if master_type == 'M':
                key_dict[mk.global_names]['Default'] = (mk, [])
            elif master_type == 'L':
                database = data_dict['Data Dictionary For'].split('].[')[1]
                key_dict[mk.global_names][database] = (mk, [])

            # master_keys[global_name] = mk

    # add the master composite keys
    # master_comp_keys = {}
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        table_MCKs = defaultdict(
            list
        )  # the key_info string is the key, the value is a list of subkeys that make up the composite key
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            if key_info == '':
                continue
            re_str = r"[ML][PUE]K\d"
            search_obj = re.search(re_str, key_info)
            if search_obj:
                match = search_obj.group()
                master_type = match[0]
                type = match[1:3]
                local_name = variable['Field Name']
                if ':' in key_info:
                    global_name = key_info.split(':')[1].strip()
                else:
                    global_name = local_name
                subkey = (global_name, local_name)
                table_MCKs[match].append(subkey)

        for key_info, fields in table_MCKs.items():
            type = key_info[1:3]
            master_type = key_info[0]

            mck = Key(frozenset(fields), type, master_type, dd_for)
            if master_type == 'M':
                key_dict[mck.global_names]['Default'] = (mck, [])
            elif master_type == 'L':
                server = dd_for.split('].[')[1]
                key_dict[mck.global_name][server] = (mck, [])

            # master_comp_keys[master_comp_key.global_names] = master_comp_key

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
                        (global_names for global_names in key_dict.keys()
                         if len(global_names) == 1 and next(iter(
                             global_names)).lower() == col_name.lower()), None)
                    if match:
                        if database in key_dict[match]:
                            use_db = database
                        else:
                            use_db = 'Default'
                        master_key = key_dict[match][use_db][0]

                        if master_key.type == 'PK' or master_key.type == 'UK':
                            write_to_key_infos.append('FK')

                            # Add the identified key to the key_dict
                            key_dict[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FK',
                                    None, dd_for))

                        elif master_key.type == 'EK':
                            write_to_key_infos.append('FE')

                            # Add the identified key to the key_dict
                            key_dict[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FE',
                                    None, dd_for))
                else:
                    global_name = key_info.split(':')[1].strip()
                    match = next(
                        (global_names for global_names in key_dict.keys()
                         if len(global_names) == 1 and next(iter(
                             global_names)).lower() == col_name.lower()), None)

                    if match:
                        if database in key_dict[match]:
                            use_db = database
                        else:
                            use_db = 'Default'
                        master_key = key_dict[match][use_db][0]

                        if master_key.type == 'PK' or master_key.type == 'UK':
                            write_to_key_infos.append('FK: ' + global_name)

                            # Add the identified key to the key_dict
                            key_dict[match][use_db][1].append(
                                Key(frozenset([(col_name, col_name)]), 'FK',
                                    None, dd_for))
                        elif master_key.type == 'EK':
                            variable['Key Information'] = 'FE: ' + global_name

                            # Add the identified key to the key_dict
                            key_dict[match][use_db][1].append(
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

        for mck_names in key_dict.keys():
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
                        if server in key_dict[comp_key_names]:
                            use_db = server
                        else:
                            use_db = 'Default'
                        mck = key_dict[comp_key_names][use_db][0]
                        if mck.type == 'PK' or key_dict[comp_key_names] == 'UK':
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
                        if key_dict[comp_key_names].type == 'PK' or key_dict[
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


#     # Format the data dictionary information
#     data = format_json_data(json_data)

#     # Initialize the graph and subgraphs
#     G = pgv.AGraph(strict=False, directed=True)
#     subgraphs = {}
#     color_map = {}
#     color_list = generate_colors()
#     for i, database in enumerate(data):
#         color_map[database] = color_list[i]

#     for i, database in enumerate(data):
#         subgraph = G.add_subgraph(name=f'cluster_{database}',
#                                   label=database,
#                                   color=color_map[database].replace(
#                                       'light', ''))
#         subgraph.node_attr["fillcolor"] = color_map[database]
#         subgraphs[database] = subgraph

#     # key_dict is a dictionary for each shared key. The key name is the global name of the key and the value
#     # is a tuple of the master table/key and a list of the child tables/keys. e.g. {key_name: (master_key, [child_key1, child_key2])}
#     key_dict = defaultdict(lambda: (None, []))
#     # initialize key_dict with master keys
#     for global_name, master_key in master_keys.items():
#         key_dict[global_name] = (master_key, [])

#     table_nodes = {}

#     # Add nodes to the graph and fill in key_dict
#     for database, dd_list in data.items():
#         for dd in dd_list:
#             dd_for = dd['Data Dictionary For']
#             table_type = dd['Table Type']
#             table_keys = []
#             for variable in dd['Data Dictionary']:
#                 local_name = variable['Field Name']
#                 key_str = variable['Key Information']
#                 if key_str == '':
#                     continue
#                 re_str = r"M?[PUEF]K\d?"
#                 search_obj = re.search(re_str, key_str)
#                 key_type = None
#                 if search_obj:
#                     match = search_obj.group()
#                     if re.match(r"\d", match[-1]):
#                         continue  # Skip composite keys
#                     if match[0] == 'M':
#                         key_type = match[1:3]
#                         is_master = True
#                     else:
#                         key_type = match[0:2]
#                         is_master = False
#                 else:
#                     continue
#                 if key_type is None:
#                     print(
#                         f'ERROR: Key type {key_str} in {dd_for}.[{local_name}] not found'
#                     )
#                 '''
#                 If the key information has a colon and a space, then the key maps to a different key name.
#                 The global name is the key name that the key maps to.
#                 '''
#                 if ':' in variable['Key Information']:
#                     global_name = variable['Key Information'].split(
#                         ':')[1].strip()
#                 else:
#                     global_name = local_name

#                 # If the global name in the key dict has different case, then use the global name in the key dict
#                 for key in key_dict.keys():
#                     if str(global_name).lower() == str(key).lower():
#                         global_name = key
#                         break

#                 key = Key(global_name, local_name, key_type, is_master, dd_for)
#                 table_keys.append(key)
#                 if not is_master:
#                     key_dict[global_name][1].append(key)

#             node = TableNode(subgraphs[database], dd_for, table_type,
#                              table_keys)
#             table_nodes[dd_for] = node

#     # Add composite keys to key_dict
#     for database, dd_list in data.items():
#         for dd in dd_list:
#             dd_for = dd['Data Dictionary For']
#             table_keys = defaultdict(set[Key])
#             for variable in dd['Data Dictionary']:
#                 key_str = variable['Key Information']
#                 re_str = r"M?[PUEF]K\d"
#                 search_obj = re.search(re_str, key_str)
#                 if search_obj:
#                     match = search_obj.group()
#                     if match[0] == 'M':
#                         continue
#                     else:
#                         key_type = match[0:2]
#                         is_master = False
#                     local_name = variable['Field Name']
#                     if ':' in key_str:
#                         global_name = key_str.split(':')[1].strip()
#                     else:
#                         global_name = local_name
#                     table_keys[match].add(
#                         Key(global_name, local_name, key_type, is_master,
#                             dd_for))

#             for key_info, keys in table_keys.items():
#                 if key_info[0] == 'M':
#                     key_type = key_info[1:3]
#                     is_master = True
#                 else:
#                     key_type = key_info[0:2]
#                     is_master = False
#                 if not is_master:
#                     comp_key = CompositeKey(keys, key_type, is_master, dd_for)
#                     global_names = comp_key.global_names
#                     key_dict[global_names][1].append(comp_key)
#                 table_nodes[dd_for].add_key(comp_key)
#     '''
#     Drawing edges rules:
#     A master table for a particular key is a table that has the master key for that key.
#     A child table for a particular key is a table that has that key but it is not a master key.
#     For each key, we want to draw edges from the master table to the child tables.
#     '''
#     for global_name, (master_key, child_keys) in key_dict.items():
#         if not master_key or not child_keys:
#             continue
#         source = table_nodes[master_key.dd_for]
#         for child_key in child_keys:
#             target = table_nodes[child_key.dd_for]
#             edge = TableEdge(G, source, target, master_key, child_key)

#     # Scale nodes based on the number of edges
#     for node in G.nodes():
#         node.attr['width'] = 0.2 + 0.02 * len(G.neighbors(node))
#         node.attr['height'] = node.attr['width']

#     # Set subgraph attributes
#     # for subgraph in G.subgraphs():
#     #     # subgraph.graph_attr['bgcolor'] = 'mintcream'
#     #     for node in subgraph.nodes():
#     #         node.attr['shape'] = 'circle'
#     #         node.attr['style'] = 'filled'
#     #         node.attr['fillcolor'] = subgraph.node_attr['fillcolor']
#     #         node.attr['color'] = 'black'

#     # Remove reference tables if specified
#     if not show_reference_tables:
#         for table_node in table_nodes.values():
#             if table_node.table_type == 'Reference Table':
#                 G.remove_node(table_node.dd_for)

#     # Manage graph layout
#     G.layout(prog='dot')
#     G.graph_attr['overlap'] = 'false'  # Prevent overlapping nodes
#     G.graph_attr['splines'] = 'true'  # Draw curved edges
#     G.graph_attr['K'] = '2'  # Increase the spring constant
#     # G.graph_attr['bgcolor'] = 'mintcream'
#     G.graph_attr['clusterrank'] = 'local'
#     G.graph_attr['rankdir'] = 'TB'

#     G.draw(draw_path, format='svg')
#     # Remove the extraneous '\' and '\n' characters from the SVG file. Not sure why they are there.
#     with open(draw_path, 'r') as f:
#         svg = f.read()
#     svg = svg.replace('\\\n', '')
#     with open(draw_path, 'w') as f:
#         f.write(svg)

#     return G

# def search_fields(json_data,
#                   query,
#                   match_case=False,
#                   column_name='Field Name'):
#     '''
#     Parameters: json_data (list of dict): List of dictionaries containing data dictionary information
#                 search_string (str) or (list of str): String to search for in the field names
#                 match_case (bool): If True, search will be case sensitive
#     Returns: fields (list of strings): List of strings of fields that match the search criteria in format "[Server].[Database].[View].[Table].[Field]"
#     '''
#     fields = []
#     for data_dict in json_data:
#         table_name = data_dict['Data Dictionary For']
#         for variable in data_dict['Data Dictionary']:
#             if match_case:
#                 if isinstance(query, list):
#                     add = True
#                     for search in query:
#                         if search not in variable[f'{column_name}']:
#                             add = False
#                     if add:
#                         fields.append(
#                             f"{table_name}.{variable[f'{column_name}']}")
#                 elif isinstance(query, str):
#                     if query in variable['Field Name']:
#                         fields.append(
#                             f"{table_name}.{variable[f'{column_name}']}")
#             else:
#                 if isinstance(query, list):
#                     add = True
#                     for search in query:
#                         if search.lower(
#                         ) not in variable[f'{column_name}'].lower():
#                             add = False
#                     if add:
#                         fields.append(
#                             f"{table_name}.{variable[f'{column_name}']}")
#                 elif isinstance(query, str):
#                     if query.lower() in variable[f'{column_name}'].lower():
#                         fields.append(
#                             f"{table_name}.{variable[f'{column_name}']}")
#     return fields

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
    with open('results\\PROD.json', 'w') as f:
        json.dump(json_data, f, indent=4)
    # matching_fields = search_fields(json_data, ['StatusEndCode'])
    # if len(matching_fields) == 0:
    #     print('No matching fields found')
    # for field in matching_fields:
    #     print(field)

    G = build_graph(json_data,
                    'results\\subkeys.svg',
                    show_reference_tables=True)

    # json_data, master_keys = fill_keys(json_data)
