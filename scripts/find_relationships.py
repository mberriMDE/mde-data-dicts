import json
import csv
from collections import defaultdict
from pathlib import Path
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import networkx as nx
import pygraphviz as pgv
import re
import urllib.parse


class Key:

    def __init__(self, global_name: str, local_name: str, type: str,
                 is_master: bool, dd_for: str):
        self.global_name = global_name
        self.local_name = local_name
        self.global_label = global_name
        self.local_label = local_name
        self.type = type
        self.is_master = is_master
        self.dd_for = dd_for


class CompositeKey:

    def __init__(self, key_set: frozenset[Key], type: str, is_master: bool,
                 dd_for: str):
        self.keys = key_set
        self.global_names = frozenset([g.global_name for g in key_set])
        self.local_names = frozenset([l.local_name for l in key_set])
        self.global_label = '{' + ', '.join(self.global_names) + '}'
        self.local_label = '{' + ', '.join(self.local_names) + '}'
        self.type = type
        self.is_master = is_master
        self.dd_for = dd_for
        self.dict = {key.global_name: key for key in key_set}


class TableNode:

    def __init__(self, subgraph, dd_for, keys=[], url=None, **attr):
        self.subgraph = subgraph
        self.dd_for = dd_for
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
        self.node = self.subgraph.add_node(dd_for, **self.attr)

        # Set node attributes
        # self.subgraph.get_node(dd_for).attr['shape'] = 'circle'
        self.subgraph.get_node(dd_for).attr['style'] = 'filled'
        # self.subgraph.get_node(dd_for).attr['fillcolor'] = 'lightblue'
        # print(dd_for)
        # print(self.subgraph.get_node(dd_for).attr['fillcolor'])
        self.subgraph.get_node(dd_for).attr['color'] = 'black'
        self.subgraph.get_node(dd_for).attr['label'] = ''
        self.subgraph.get_node(
            dd_for).attr['tooltip'] = f'{self.view}.{self.table}'
        self.subgraph.get_node(dd_for).attr['URL'] = self.url
        print(self.subgraph.get_node(dd_for).attr['URL'])

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
        self.edge = self.graph.add_edge(graph.get_node(source.dd_for),
                                        graph.get_node(target.dd_for),
                                        dir="back",
                                        **self.attr)

        tooltip = f'{source.dd_for}.[{source_key.local_label}]\n <- {target.dd_for}.[{target_key.local_label}]'
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
        self.graph.get_edge(source.dd_for,
                            target.dd_for).attr['tooltip'] = tooltip


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


def fill_keys(json_data, generate_excel=True):
    '''
    Fill in missing foreign keys in the data dictionary information.

    Args:
        json_data (list of dict): List of dictionaries containing data dictionary information
        generate_excel (bool): If True, generate new excel files with filled in foreign keys and composite keys in filled\\
    
    Returns:
        json_data (list of dict): List of dictionaries containing data dictionary information with filled in foreign keys
    '''
    # Dictionary to hold all master keys with their types and tables
    master_keys = {}
    for data_dict in json_data:
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            if key_info == '':
                continue
            re_str = r"M[PUE]K\d?"
            search_obj = re.search(re_str, key_info)
            if search_obj:
                match = search_obj.group()
                if re.search(r"\d", match) is not None:
                    continue  # Skip composite keys
                if match[0] == 'M':
                    key_type = match[1:3]
                    is_master = True
                else:
                    continue
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
        dd_for = data_dict['Data Dictionary For']
        table_MCKs = defaultdict(
            list
        )  # the key_info string is the key, the value is a list of subkeys that make up the composite key
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            if key_info == '':
                continue
            re_str = r"M[PUE]K\d"
            search_obj = re.search(re_str, key_info)
            if search_obj:
                match = search_obj.group()
                is_master = True
                type = match[1:3]
                local_name = variable['Field Name']
                if ':' in key_info:
                    global_name = key_info.split(':')[1].strip()
                else:
                    global_name = local_name
                subkey = Key(global_name, local_name, type, is_master, dd_for)
                table_MCKs[match].append(subkey)

        for key_info, subkeys in table_MCKs.items():
            type = key_info[1:3]
            is_master = True
            key_set = set()
            for subkey in subkeys:
                key_set.add(subkey)
            master_comp_key = CompositeKey(frozenset(key_set), type, is_master,
                                           dd_for)
            master_comp_keys[master_comp_key.global_names] = master_comp_key

    # Fill in missing foreign keys
    for data_dict in json_data:
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            col_name = variable['Field Name']
            if len(key_info) > 0:
                if key_info[0] == 'M':  # Skip master keys
                    continue
            if ':' not in key_info:
                # ks = master_keys.keys().tolist()
                match = next((key for key in master_keys.keys()
                              if key.lower() == col_name.lower()), None)
                if match:
                    if master_keys[match].type == 'PK' or master_keys[
                            match].type == 'UK':
                        variable['Key Information'] = 'FK'
                    elif master_keys[match].type == 'EK':
                        variable['Key Information'] = 'EK'

    # Fill in missing composite keys
    for data_dict in json_data:
        # Get a set of all the fields in the data dictionary
        subkeys = set()
        present_comp_keys = defaultdict(set)
        count = 1
        for variable in data_dict['Data Dictionary']:
            subkeys.add(variable['Field Name'])
            # Add the global names if they exist
            splut = variable['Key Information'].split(':')
            if len(splut) > 1:
                subkeys.add(splut[1].strip())
        lower_subkeys = set(subkey.lower() for subkey in subkeys)
        for mck_names in master_comp_keys.keys():
            lower_mck_names = set(c.lower() for c in mck_names)
            if lower_mck_names.issubset(lower_subkeys):
                present_comp_keys[mck_names] = count
                count += 1
        for variable in data_dict['Data Dictionary']:
            key_info = variable['Key Information']
            col_name = variable['Field Name']
            if len(key_info) > 0:
                if key_info[0] == 'M':
                    continue
            if key_info == '' or ':' not in key_info:  # Check if the local name is in the composite key
                for comp_key_names in present_comp_keys:
                    comp_key_names_lower = set(c.lower()
                                               for c in comp_key_names)
                    if col_name.lower() in comp_key_names_lower:
                        if master_comp_keys[
                                comp_key_names].type == 'PK' or master_comp_keys[
                                    comp_key_names] == 'UK':
                            variable[
                                'Key Information'] = f'FK{present_comp_keys[comp_key_names]}'
                        elif master_comp_keys[comp_key_names].type == 'EK':
                            variable[
                                'Key Information'] = f'EK{present_comp_keys[comp_key_names]}'
            if ':' in key_info:  # Check if the global name is in the composite key
                global_name = key_info.split(':')[1].strip()
                for comp_key_names in present_comp_keys:
                    comp_key_names_lower = set(c.lower()
                                               for c in comp_key_names)
                    if global_name.lower() in comp_key_names_lower:
                        if master_comp_keys[
                                comp_key_names].type == 'PK' or master_comp_keys[
                                    comp_key_names] == 'UK':
                            variable[
                                'Key Information'] = f'FK{present_comp_keys[comp_key_names]}'

    master_keys.update(master_comp_keys)

    if generate_excel:
        for data_dict in json_data:
            dd_for = data_dict['Data Dictionary For']
            names = dd_for[1:-1].split('].[')
            server = names[0]
            database = names[1]
            view = names[2]
            table = names[3]
            dd_json_to_excel(
                json.dumps(data_dict, indent=4),
                f'filled\\{server}\\{database}\\{view}\\{database}.{view}.{table}_data_dict.xlsx'
            )

    return json_data, master_keys


def build_graph(json_data, draw_path):
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
    G = pgv.AGraph(strict=False, directed=True)
    subgraphs = {}
    color_map = {}
    color_list = generate_colors()
    for i, database in enumerate(data):
        color_map[database] = color_list[i]

    for i, database in enumerate(data):
        subgraph = G.add_subgraph(name=f'cluster_{database}',
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
                re_str = r"M?[PUEF]K\d?"
                search_obj = re.search(re_str, key_str)
                key_type = None
                if search_obj:
                    match = search_obj.group()
                    if re.match(r"\d", match[-1]):
                        continue  # Skip composite keys
                    if match[0] == 'M':
                        key_type = match[1:3]
                        is_master = True
                    else:
                        key_type = match[0:2]
                        is_master = False
                else:
                    continue
                if key_type is None:
                    print(
                        f'ERROR: Key type {key_str} in {dd_for}.[{local_name}] not found'
                    )
                '''
                If the key information has a colon and a space, then the key maps to a different key name.
                The global name is the key name that the key maps to.
                '''
                if ':' in variable['Key Information']:
                    global_name = variable['Key Information'].split(
                        ':')[1].strip()
                else:
                    global_name = local_name

                # If the global name in the key dict has different case, then use the global name in the key dict
                for key in key_dict.keys():
                    if global_name.lower() == key.lower():
                        global_name = key
                        break

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
            table_keys = defaultdict(set[Key])
            for variable in dd['Data Dictionary']:
                key_str = variable['Key Information']
                re_str = r"M?[PUEF]K\d"
                search_obj = re.search(re_str, key_str)
                if search_obj:
                    match = search_obj.group()
                    if match[0] == 'M':
                        continue
                    else:
                        key_type = match[0:2]
                        is_master = False
                    local_name = variable['Field Name']
                    if ':' in key_str:
                        global_name = key_str.split(':')[1].strip()
                    else:
                        global_name = local_name
                    table_keys[match].add(
                        Key(global_name, local_name, key_type, is_master,
                            dd_for))

            for key_info, keys in table_keys.items():
                if key_info[0] == 'M':
                    key_type = key_info[1:3]
                    is_master = True
                else:
                    key_type = key_info[0:2]
                    is_master = False
                if not is_master:
                    comp_key = CompositeKey(keys, key_type, is_master, dd_for)
                    global_names = comp_key.global_names
                    key_dict[global_names][1].append(comp_key)
                table_nodes[dd_for].add_key(comp_key)
    '''
    Drawing edges rules:
    A master table for a particular key is a table that has the master key for that key.
    A child table for a particular key is a table that has that key but it is not a master key.
    For each key, we want to draw edges from the master table to the child tables.
    
    '''
    for global_name, (master_key, child_keys) in key_dict.items():
        if not master_key or not child_keys:
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
        # subgraph.graph_attr['bgcolor'] = 'mintcream'
        for node in subgraph.nodes():
            node.attr['shape'] = 'circle'
            node.attr['style'] = 'filled'
            node.attr['fillcolor'] = subgraph.node_attr['fillcolor']
            node.attr['color'] = 'black'

    # Manage graph layout
    G.layout(prog='dot')
    G.graph_attr['overlap'] = 'false'  # Prevent overlapping nodes
    G.graph_attr['splines'] = 'true'  # Draw curved edges
    G.graph_attr['K'] = '2'  # Increase the spring constant
    # G.graph_attr['bgcolor'] = 'mintcream'
    G.graph_attr['clusterrank'] = 'local'

    G.draw(draw_path, format='svg')
    # Remove the extraneous '\' and '\n' characters from the SVG file. Not sure why they are there.
    with open(draw_path, 'r') as f:
        svg = f.read()
    svg = svg.replace('\\\n', '')
    with open(draw_path, 'w') as f:
        f.write(svg)

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
    json_data = load_json_data(files)
    with open('results\\MDEORG.json', 'w') as f:
        json.dump(json_data, f, indent=4)
    # matching_fields = search_fields(json_data, ['StatusEndCode'])
    # if len(matching_fields) == 0:
    #     print('No matching fields found')
    # for field in matching_fields:
    #     print(field)

    G = build_graph(json_data, 'results\\subgraphs.svg')

    # json_data, master_keys = fill_keys(json_data)
