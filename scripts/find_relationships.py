import json
import csv
from collections import defaultdict
from pathlib import Path
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import networkx as nx
import pygraphviz as pgv
import re


class Key:

    def __init__(self, global_name: str, local_name: str, type: str,
                 is_master: bool, dd_for: str):
        self.global_name = global_name
        self.local_name = local_name
        self.type = type
        self.is_master = is_master
        self.dd_for = dd_for


class CompositeKey:

    def __init__(self, global_names: frozenset, type: str, is_master: bool,
                 dd_for: str):
        self.global_name = global_names
        self.type = type
        self.is_master = is_master
        self.dd_for = dd_for


class TableNode:

    def __init__(self, subgraph, dd_for, keys=[], url=None, **attr):
        self.subgraph = subgraph
        self.dd_for = dd_for
        self.keys = keys
        self.url = url
        self.attr = attr

        # Table naming convention: [server].[database].[view].[table]
        names = dd_for[1:-1].split('].[')  # Convert bracketed names to list
        self.server = names[0]
        self.database = names[1]
        self.view = names[2]
        self.table = names[3]

        # Create the node in the graph
        self.node = self.subgraph.add_node(dd_for, **self.attr)

        # Set node attributes
        # self.subgraph.get_node(dd_for).attr['shape'] = 'circle'
        self.subgraph.get_node(dd_for).attr['style'] = 'filled'
        # self.subgraph.get_node(dd_for).attr['fillcolor'] = 'lightblue'
        # print(dd_for)
        # print(self.subgraph.get_node(dd_for).attr['fillcolor'])
        self.subgraph.get_node(dd_for).attr['color'] = 'black'
        self.subgraph.get_node(dd_for).attr['label'] = self.table
        if url:
            self.subgraph.get_node(dd_for).attr['URL'] = url

    def add_key(self, key):
        self.keys.append(key)


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
        self.edge = self.graph.add_edge(graph.get_node(source.dd_for),
                                        graph.get_node(target.dd_for),
                                        **self.attr)

        # Set edge attributes based on metadata
        # self.graph.get_edge(
        #     source.dd_for,
        #     target.dd_for).attr['label'] = source_key.global_name
        self.graph.get_edge(
            source.dd_for, target.dd_for
        ).attr['color'] = 'blue' if self.same_server else 'red'
        self.graph.get_edge(
            source.dd_for, target.dd_for
        ).attr['style'] = 'solid' if self.same_database else 'dashed'


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
        "lightblue",
        "lightgreen",
        "lightred",
        "lightorange",
        "lightyellow",
        "lightpurple",
        "lightcyan",
        "lightbrown",
        "lightgray",
    ]
    return colors


def fill_keys(json_data):
    '''
    Fill in missing foreign keys in the data dictionary information.

    Args:
        json_data (list of dict): List of dictionaries containing data dictionary information
    
    Returns:
        json_data (list of dict): List of dictionaries containing data dictionary information with filled in foreign keys
    '''
    # Dictionary to hold all master keys with their types and tables
    master_keys = {}
    for data_dict in json_data:
        for variable in data_dict['Data Dictionary']:
            key_str = variable['Key Information']
            if key_str == '':
                continue
            master_strs = ['MPK', 'MUK', 'MEK']
            is_master = any(master_str in key_str
                            for master_str in master_strs)
            if is_master:
                key_type = key_str[1:3]
            else:
                continue
            '''
            If the key information has a colon and a space, then the key maps to a different key name.
            The global name is the key name that the key maps to.
            '''
            if ': ' in variable['Key Information']:
                global_name = variable['Key Information'].split(': ')[1]
            else:
                global_name = variable['Field Name']
            mk = Key(global_name, variable['Field Name'], key_type, is_master,
                     data_dict['Data Dictionary For'])
            master_keys[global_name] = mk

    # add the master composite keys
    master_comp_keys = {}
    for data_dict in json_data:
        table_MCKs = defaultdict(list)
        for variable in data_dict['Data Dictionary']:
            key_str = variable['Key Information']
            if key_str == '':
                continue
            re_str = r"M[PUK]K\d{1}"
            search_obj = re.search(re_str, key_str)
            if search_obj:
                match = search_obj.group()
                table_MCKs[match].append(variable['Field Name'])
        for key, fields in table_MCKs.items():
            type = key[1:3]
            is_master = True
            global_names = frozenset(fields)
            mck = CompositeKey(global_names, type, is_master,
                               data_dict['Data Dictionary For'])
            master_comp_keys[global_names] = mck

    # Fill in missing foreign keys
    for data_dict in json_data:
        for variable in data_dict['Data Dictionary']:
            key_str = variable['Key Information']
            col_name = variable['Field Name']
            if key_str == '':
                # ks = master_keys.keys().tolist()
                match = next((key for key in master_keys.keys()
                              if key.lower() == col_name.lower()), None)
                if match:
                    if master_keys[match].type == 'PK' or master_keys[
                            match] == 'UK':
                        variable['Key Information'] = 'FK'
                    elif master_keys[match].type == 'EK':
                        variable['Key Information'] = 'EK'

    # Fill in missing composite keys
    for data_dict in json_data:
        # Get a set of all the fields in the data dictionary
        fields = set()
        present_CKs = set()
        count = 1
        for variable in data_dict['Data Dictionary']:
            fields.add(variable['Field Name'])
        lower_fields = set(field.lower() for field in fields)
        for MCK in master_comp_keys.keys():
            lower_MCK = set(c.lower() for c in MCK)
            if lower_MCK.issubset(lower_fields):
                present_CKs.add(MCK)
        for variable in data_dict['Data Dictionary']:
            key_str = variable['Key Information']
            col_name = variable['Field Name']
            if key_str == '':
                for CK in present_CKs:
                    if col_name.lower() in CK:
                        if master_comp_keys[
                                CK].type == 'PK' or master_comp_keys[
                                    CK] == 'UK':
                            variable['Key Information'] = f'FK{count}'
                        elif master_comp_keys[CK].type == 'EK':
                            variable['Key Information'] = f'EK{count}'
                        count += 1

    master_keys.update(master_comp_keys)

    return json_data, master_keys


def build_graph(json_data):
    '''
    Parameters: json_data (list of dictionaries): List of dictionaries containing data dictionary information
    Returns: G: A directed graph where each node is a table and each edge is a foreign key relationship.

    PK = Primary Key
    UK = Unique Key
    EK = Entity Key
    FK = Foreign Key

    If the global name of the key is different than the field name, 
    start by mapping PKs and UKs to FKs in external tables. PKs and UKs should map to PKs, UKs of the same
    name in external tables
    '''
    # Fill in missing foreign keys
    json_data, master_keys = fill_keys(json_data)

    # Format the data dictionary information
    data = format_json_data(json_data)

    # Initialize the graph and subgraphs
    G = pgv.AGraph(strict=True, directed=False)
    subgraphs = {}
    color_map = {}
    color_list = generate_colors()
    for i, database in enumerate(data):
        color_map[database] = color_list[i]

    for i, database in enumerate(data):
        subgraph = G.add_subgraph(name=database,
                                  label=database,
                                  color=color_map[database].replace(
                                      'light', ''))
        subgraph.node_attr["fillcolor"] = color_map[database]
        subgraphs[database] = subgraph

    # key_dict is a dictionary for each shared key. The key name is the global name of the key and the value
    # is a tuple of the master table/key and a list of the child tables/keys. e.g. {key_name: (master_key, [child_key1, child_key2])}
    key_dict = defaultdict(lambda: (None, []))
    # initialize key_dict with master keys
    for global_name, master_key in master_keys.items():
        key_dict[global_name] = (master_key, [])

    table_nodes = {}

    # Add nodes to the graph and fill in key_dict
    for database, dd_list in data.items():
        for dd in dd_list:
            dd_for = dd['Data Dictionary For']
            table_keys = []
            for variable in dd['Data Dictionary']:
                local_name = variable['Field Name']
                key_str = variable['Key Information']
                if key_str == '':
                    continue
                master_strs = ['MPK', 'MUK', 'MEK']
                is_master = any(master_str in key_str
                                for master_str in master_strs)
                if is_master:
                    key_type = key_str[1:3]
                else:
                    key_type = key_str[0:2]
                '''
                If the key information has a colon and a space, then the key maps to a different key name.
                The global name is the key name that the key maps to.
                '''
                if ': ' in variable['Key Information']:
                    global_name = variable['Key Information'].split(': ')[1]
                else:
                    global_name = local_name
                key = Key(global_name, local_name, key_type, is_master, dd_for)
                table_keys.append(key)
                if not is_master:
                    key_dict[global_name][1].append(key)

            node = TableNode(subgraphs[database], dd_for, table_keys)
            table_nodes[dd_for] = node

    # Add composite keys to key_dict
    for database, dd_list in data.items():
        for dd in dd_list:
            dd_for = dd['Data Dictionary For']
            table_keys = defaultdict(set)
            for variable in dd['Data Dictionary']:
                key_str = variable['Key Information']
                re_str = r"M?[PUK]K\d"
                search_obj = re.search(re_str, key_str)
                if search_obj:
                    match = search_obj.group()
                    table_keys[match].add(variable['Field Name'])
            for key_info, fields in table_keys.items():
                if key_info[0] == 'M':
                    type = key_info[1:3]
                    is_master = True
                else:
                    type = key_info[0:2]
                    is_master = False
                global_names = frozenset(fields)
                comp_key = CompositeKey(global_names, type, is_master, dd_for)
                if not is_master:
                    key_dict[global_names][1].append(comp_key)
                G.get_node(dd_for).add_key(comp_key)
    '''
    Drawing edges rules:
    A master table for a particular key is a table that has the master key for that key.
    A child table for a particular key is a table that has that key but it is not a master key.
    For each key, we want to draw edges from the master table to the child tables.
    
    '''
    for global_name, (master_key, child_keys) in key_dict.items():
        if not master_key:
            continue
        source = table_nodes[master_key.dd_for]
        for child_key in child_keys:
            target = table_nodes[child_key.dd_for]
            edge = TableEdge(G, source, target, master_key, child_key)

    # Scale nodes based on the number of edges
    for node in G.nodes():
        node.attr['width'] = 0.2 + 0.02 * len(G.neighbors(node))
        node.attr['height'] = node.attr['width']

    # Set subgraph attributes
    for subgraph in G.subgraphs():
        print(subgraph.name)
        subgraph.graph_attr['bgcolor'] = 'blue'
        for node in subgraph.nodes():
            node.attr['shape'] = 'circle'
            node.attr['style'] = 'filled'
            node.attr['fillcolor'] = subgraph.node_attr['fillcolor']
            node.attr['color'] = 'black'

    # Manage graph layout
    G.layout(prog='dot')
    G.graph_attr['overlap'] = 'false'  # Prevent overlapping nodes
    G.graph_attr['splines'] = 'true'  # Draw curved edges

    return G


def search_fields(json_data,
                  query,
                  match_case=False,
                  column_name='Field Name'):
    '''
    Parameters: json_data (list of dict): List of dictionaries containing data dictionary information
                search_string (str) or (list of str): String to search for in the field names
                match_case (bool): If True, search will be case sensitive
    Returns: fields (list of strings): List of strings of fields that match the search criteria in format "[Server].[Database].[View].[Table].[Field]"
    '''
    fields = []
    for data_dict in json_data:
        table_name = data_dict['Data Dictionary For']
        for variable in data_dict['Data Dictionary']:
            if match_case:
                if isinstance(query, list):
                    add = True
                    for search in query:
                        if search not in variable[f'{column_name}']:
                            add = False
                    if add:
                        fields.append(
                            f"{table_name}.{variable[f'{column_name}']}")
                elif isinstance(query, str):
                    if query in variable['Field Name']:
                        fields.append(
                            f"{table_name}.{variable[f'{column_name}']}")
            else:
                if isinstance(query, list):
                    add = True
                    for search in query:
                        if search.lower(
                        ) not in variable[f'{column_name}'].lower():
                            add = False
                    if add:
                        fields.append(
                            f"{table_name}.{variable[f'{column_name}']}")
                elif isinstance(query, str):
                    if query.lower() in variable[f'{column_name}'].lower():
                        fields.append(
                            f"{table_name}.{variable[f'{column_name}']}")
    return fields


if __name__ == "__main__":
    if not Path('results').exists():
        Path('results').mkdir()

    directories = ['data\\SQLPROD01\\MARSS', 'data\\SQLPROD01\\MDEORG']
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    # print(files)
    json_data = load_json_data(files)
    with open('results\\MDEORG.json', 'w') as f:
        json.dump(json_data, f, indent=4)
    # matching_fields = search_fields(json_data, ['StatusEndCode'])
    # if len(matching_fields) == 0:
    #     print('No matching fields found')
    # for field in matching_fields:
    #     print(field)

    G = build_graph(json_data)
    G.draw('results\\MDEORG.svg', format='svg')
