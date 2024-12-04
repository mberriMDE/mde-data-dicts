import json
import csv
from collections import defaultdict
from pathlib import Path
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import networkx as nx
import pygraphviz as pgv
import re
import urllib.parse
import math

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
                 dd_for: str,
                 master_type: str = None,
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
            try:
                self.global_label = next(iter(self.global_names))
                self.local_label = next(iter(self.local_names))
            except StopIteration:
                print(self.global_names)
                print(self.local_names)
                self.global_label = self.global_names
                self.local_label = self.local_names

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
    json_data = []
    for file_path in file_paths:
        if 'data_dict' not in file_path:
            continue
        json_str = dd_excel_to_json(file_path)
        data_dict = json.loads(json_str)
        data_dict["File Path"] = file_path
        json_data.append(data_dict)
    return json_data


# Write the json data to excel files
def write_json_data(json_data, replaced, replacer):
    for data_dict in json_data:
        new_file_path = data_dict["File Path"].replace(replaced, replacer)
        json_str = json.dumps(data_dict, indent=4)
        dd_json_to_excel(json_str, new_file_path)


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
            key_type = keystring[1:3]
            master_type = keystring[0:1]
            equivalent_key_set = next(
                (frozenset(equivalent_keys[k])
                 for k in equivalent_keys if k.lower() == global_name.lower()),
                None)
            key = Key(key_set, key_type, dd_for, master_type,
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
              overwrite=True,
              equivalent_fields=None):
    '''
    Fill in missing foreign keys in the data dictionary information.

    Args:
        json_data (list[dict]): List of dictionaries containing data dictionary information
        key_dict_masters (defaultdict(lambda: defaultdict(lambda: (None, []))): Dictionary containing only the master keys information.
        overwrite (bool): If True, the already present non-master key strings should be overwritten with the correct non-master key strings
        equivalent keys (dict): Maps a master key field to a list of fields that form a composite key of equivalent information
    
    Returns:
        json_data (list[dict]): List of dictionaries containing data dictionary information with filled in foreign keys.

        key_dict (defaultdict(lambda: defaultdict(lambda: (None, []))): Dictionary containing the keys information.The outer dict key is 
            the global name of a shared key. The value is the inner dictionary. The 'Default' dictionary key
            in the inner dictionary stores the regular master key for a particular global name. The remaining inner dictionary keys 
            store local master keys with the relevant database being the inner dictionary key. The inner dictionary values are tuples of 
            the master key and a list of the child keys (empty for this function).
            example:
            {
                'global_name1': {
                                    'Default': (master_key, [])
                                    'server1.database1': (local_master_key, [])
                                }
            }
    '''

    # map from lowercase global name to global name
    global_lower_to_upper = {
        global_name.lower(): global_name
        for global_name in key_dict_masters
    }
    for equivalents in equivalent_fields.values():
        for global_name in equivalents:
            global_lower_to_upper[global_name.lower()] = global_name

    # Fill in missing foreign keys and add them to key_dict
    key_dict = key_dict_masters
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        # if '[OrganizationType]' in dd_for:
        #     print('here')
        server = dd_for[1:-1].split('].[')[0]
        database = f"{server}.{dd_for.split('].[')[1]}"
        for variable in data_dict['Data Dictionary']:
            info_list = variable['Key Information'].split(',')
            info_list = [i.strip() for i in info_list]
            write_to_key_info = []
            local_name = variable['Field Name']
            lower_global = None
            pop_string = None
            key_type = 'ERROR'

            skip = False
            write = False
            for info in info_list:
                if re.match(r"^[MLS]?[PUEF][KE]\d?$", info):  # key string case
                    if overwrite:
                        write = True
                    if info[0] == 'M' or info[0] == 'L':  # Skip master keys
                        skip = True
                        break
                    if info == 'PK':  # Foreign primary key
                        key_type = info
                else:
                    write = True

                if info.startswith('G:'):  # global name case
                    global_name = info.split(':')[1].strip()
                    lower_global = global_name.lower()
                    if lower_global not in global_lower_to_upper:
                        global_lower_to_upper[lower_global] = global_name

                if info in ['D', 'O']:  # pop string case
                    pop_string = info

            if skip:
                continue
            if lower_global is not None:
                if 'courseleveltype' in lower_global:
                    print(dd_for)
                write_to_key_info.append(
                    f'G: {global_lower_to_upper[lower_global]}')
            else:
                # Default to the field name if no global name is specified
                lower_global = local_name.lower()

            if pop_string:
                write_to_key_info.append(pop_string)

            # This statement finds the global name of the first master key that matches the column name
            match = next((master_name
                          for master_name in key_dict_masters.keys()
                          if master_name.lower() == lower_global), None)
            if match:
                if database in key_dict_masters[match]:
                    use_db = database
                else:
                    use_db = 'Default'
                master_key = key_dict_masters[match][use_db][0]
                # if master_key is None:
                # print('here')

                if key_type != 'PK':
                    if master_key.type == 'EK':
                        key_type = 'FE'
                    else:
                        key_type = 'FK'

                # Add the identified key to the key_dict
                key_dict_masters[match][use_db][1].append(
                    Key(frozenset([(match, local_name)]),
                        type=key_type,
                        dd_for=dd_for,
                        equivalent_key_set=master_key.equivalent_key_set))

                write_to_key_info.insert(0, key_type)
            if write:
                variable['Key Information'] = ', '.join(write_to_key_info)
        # dd_json_to_excel(json.dumps(data_dict, indent=4),
        #                  output_file=f'data/intermediate/{dd_for}.xlsx')

    # Fill in missing composite keys
    for data_dict in json_data:
        dd_for = data_dict['Data Dictionary For']
        server = dd_for[1:-1].split('].[')[0]
        database = f"{server}.{dd_for.split('].[')[1]}"
        # Get a set of all the fields in the data dictionary
        lower_fields = set()
        local_names = {}

        # Dictionary to hold the composite keys that are present in the data dictionary along with the composite suffix (count)
        present_mcks = defaultdict(set)
        count = 1
        for variable in data_dict['Data Dictionary']:
            lower_global = None
            # Add the global name of the field to the set of fields
            info_list = variable['Key Information'].split(',')
            for info in info_list:
                if info.startswith('G:'):
                    lower_global = info.split(':')[1].strip()
                    break
            if lower_global is None:
                lower_global = variable['Field Name'].lower()
            lower_fields.add(lower_global)

        for mk_name in key_dict_masters.keys():
            # if mk_name.lower() == 'stateorganizationid':
            #     print('here')
            if mk_name not in equivalent_fields.keys():
                continue

            if mk_name.lower(
            ) in lower_fields:  # Don't bother with keys that are already in the data dictionary
                continue

            mck_set = frozenset(equivalent_fields[mk_name])

            # Mark the composite key if it's present in the data dictionary
            lower_mck_set = frozenset(c.lower() for c in mck_set)

            # The intersection of the composite key with the set of fields in the data dictionary
            intersection = set(lower_mck_set.intersection(lower_fields))

            if len(intersection) > 0:
                present_mcks[lower_mck_set] = {
                    'count': count,
                    'mk_name': mk_name,
                    'remaining': intersection,
                    'components': set(),
                    'use_db': None,
                    'type': None
                }
                # The 'count' is used to identify the composite key
                # the 'mk_name' is used to identify the associated master key
                # the 'remaining' is used to identify the remaining composite keys components
                # the 'components' is for storing the set of global/local name pairs
                count += 1
        # if '[Assessment_WIDA_' in dd_for:
        #     print('here')
        for variable in data_dict['Data Dictionary']:
            info_list = [
                info.strip() for info in variable['Key Information'].split(',')
            ]
            local_name = variable['Field Name']
            pop_string = None
            lower_global = None
            skip = False
            write = True
            write_to_key_info = []

            # Add the current info list items to be written
            key_string = None
            for info in info_list:
                if re.match(r"^[MLS]?[PUEF][KE]\d?$", info):
                    if not overwrite:
                        skip = True
                        write = False
                        break
                    else:
                        key_string = info
                    # if info[0] == 'M' or info[0] == 'L':
                    #     skip = True
                    #     write = False
                    #     break
                if info.startswith('G:'):  # Global name
                    lower_global = info.split(':')[1].strip().lower()
                    write_to_key_info.append(
                        f'G: {global_lower_to_upper[lower_global]}')
                if info in ['O', 'D']:  # Population string
                    pop_string = info
                    write_to_key_info.append(pop_string)

            if skip:
                continue

            # Retain the info list items
            if lower_global is None:
                lower_global = local_name.lower()

            local_names[lower_global] = local_name

            for comp_key_names in present_mcks:
                if lower_global in comp_key_names and lower_global in present_mcks[
                        comp_key_names]['remaining']:

                    # Remove the used component from the set
                    present_mcks[comp_key_names]['remaining'].remove(
                        lower_global)

                    # Add the global/local name pair to the set
                    present_mcks[comp_key_names]['components'].add(
                        (global_lower_to_upper[lower_global],
                         local_names[lower_global]))

                    current_count = present_mcks[comp_key_names]['count']
                    mck_name = present_mcks[comp_key_names]['mk_name']

                    if database in key_dict_masters[mck_name]:
                        use_db = database
                    else:
                        use_db = 'Default'

                    present_mcks[comp_key_names]['use_db'] = use_db

                    master_key = key_dict_masters[mck_name][use_db][0]

                    if master_key.type == 'PK' or master_key.type == 'UK':
                        key_type = 'FK'
                    elif master_key.type == 'EK':
                        key_type = 'FE'

                    present_mcks[comp_key_names]['type'] = key_type

                    key_string = f'S{key_type}{current_count}: {mck_name}'

            if key_string is not None:
                write_to_key_info.insert(0, key_string)
            if write:
                # if None in write_to_key_info:
                #     # print('here')
                #     write_to_key_info.remove(None)
                variable['Key Information'] = ', '.join(write_to_key_info)

        for mck, vals in present_mcks.items():
            # if len(vals['remaining']) > 0:
            key = Key(vals['components'],
                      type=vals['type'],
                      dd_for=dd_for,
                      subset_of=vals['mk_name'])
            key_dict[vals['mk_name']][vals['use_db']][1].append(key)

    return (json_data, key_dict)


def graph_to_json(G):
    nodes = []
    for dd_for in G.nodes():
        node = {
            'id': dd_for,
            'tooltip': G.get_node(dd_for).attr['tooltip'],
            'url': G.get_node(dd_for).attr['URL'],
            'subgraph': dd_for[1:-1].split('].[')[1]
        }
        nodes.append(node)

    edges = []
    for edge in G.edges():
        edges.append({'source': edge[0], 'target': edge[1]})
    graph_json = {'nodes': nodes, 'edges': edges}
    return graph_json


def build_graph(json_data, key_dict, show_reference_tables=True):
    '''
    Args:
        json_data (list of dict): List of dictionaries containing data dictionary information
        key_dict (defaultdict(lambda: defaultdict(lambda: (None, []))): Dictionary containing the keys information.The outer dict key is 
            the global name of a shared key. The value is the inner dictionary. The 'Default' dictionary key
            in the inner dictionary stores the regular master key for a particular global name. The remaining inner dictionary keys 
            store local master keys with the relevant database being the inner dictionary key. The inner dictionary values are tuples of 
            the master key and a list of the child keys (empty for this function).
            example:
            {
                'global_name1': {
                                    'Default': (master_key, [])
                                    'server1.database1': (local_master_key, [])
                                }
            }
        draw_path (str): Path to save the graph image
        show_reference_tables (bool): Indicates whether to show the reference tables

    Returns:
        G (pgv.AGraph): Graph object containing the data dictionary relationships

    If the global name of the key is different than the field name, 
    start by mapping PKs and UKs to FKs in external tables. PKs and UKs should map to PKs, UKs of the same
    name in external tables
    '''
    data = format_json_data(json_data)

    # Initialize graph and subgraphs
    G = pgv.AGraph(strict=False, directed=True)
    subgraphs = {}
    color_map = {}
    color_list = generate_colors()
    for i, database in enumerate(data):
        color_map[database] = color_list[i]
        subgraph = G.add_subgraph(name=f'cluster_{database}',
                                  label=database,
                                  color=color_map[database].replace(
                                      'light', ''))
        subgraphs[database] = subgraph
        subgraph.node_attr["fillcolor"] = color_map[database]

    # Add nodes
    table_nodes = {}
    for database, data_dicts in data.items():
        for data_dict in data_dicts:
            dd_for = data_dict['Data Dictionary For']
            table_type = data_dict['Table Type']
            node = TableNode(subgraphs[database], dd_for, table_type)
            table_nodes[dd_for] = node

    # Add edges
    for global_name, database_dicts in key_dict.items():
        default_master_key = database_dicts['Default'][0]
        for database, (master_key, child_keys) in database_dicts.items():
            if master_key is None:
                continue
            table_nodes[master_key.dd_for].add_key(master_key)
            source = table_nodes[master_key.dd_for]
            for child_key in child_keys:
                table_nodes[child_key.dd_for].add_key(child_key)
                target = table_nodes[child_key.dd_for]
                edge = TableEdge(G, source, target, master_key, child_key)

            if database != 'Default':
                source = table_nodes[default_master_key.dd_for]
                target = table_nodes[master_key.dd_for]
                edge = TableEdge(G,
                                 source,
                                 target,
                                 default_master_key,
                                 master_key,
                                 color='blue')

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
    G.graph_attr['rankdir'] = 'TB'  # Top to Bottom layout

    return G


def generate_graph_svg(G, path):
    G.draw(path, format='svg')

    # Remove the extraneous '\' and '\n' characters from the SVG file. Not sure why they are there.
    with open(path, 'r') as f:
        svg = f.read()
    svg = svg.replace('\\\n', '')
    with open(path, 'w') as f:
        f.write(svg)


if __name__ == "__main__":

    directories = ['data\\excel_dds\\EDU-SQLPROD01']
    files = []
    for directory in directories:
        files.extend(list_files(directory))
    json_data = load_json_data(files)

    with open('data\\equivalent_fields.json', 'r') as f:
        equivalent_keys = json.load(f)
    key_dict_masters = find_master_keys(json_data, equivalent_keys)

    final_data, key_dict = fill_keys(json_data,
                                     key_dict_masters,
                                     overwrite=True,
                                     equivalent_fields=equivalent_keys)

    write_json_data(final_data, 'excel_dds', 'excel_dds_filled')

    G = build_graph(json_data, key_dict)
    graph_json = graph_to_json(G)

    with open('mde-data-dicts\\docs\\graph.json', 'w') as f:
        f.write(json.dumps(graph_json, indent=4))
