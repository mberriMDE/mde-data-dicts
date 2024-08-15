import json
import csv
from collections import defaultdict
from pathlib import Path
from json_excel_conversion import dd_json_to_excel, dd_excel_to_json
import networkx as nx
import pygraphviz as pgv


class Key:

    def __init__(self, global_name: str, local_name: str, type: str):
        self.global_name = global_name
        self.local_name = local_name
        self.type = type


class TableNode:

    def __init__(self, graph, dd_for, keys=[], url=None, **attr):
        self.graph = graph
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
        self.node = self.graph.add_node(dd_for, **self.attr)

        # Set node attributes
        self.graph.get_node(dd_for).attr['shape'] = 'box'
        self.graph.get_node(dd_for).attr['style'] = 'filled'
        self.graph.get_node(dd_for).attr['fillcolor'] = 'lightblue'
        # self.graph.get_node(dd_for).attr['label'] = f"{self.table}\n{', '.join(self.keys)}"
        if url:
            self.graph.get_node(dd_for).attr['URL'] = url


class TableEdge:

    def __init__(self, graph: pgv.AGraph, source: 'TableNode',
                 target: 'TableNode', source_key_type: str,
                 target_key_type: str, key_name: str, **attr):
        self.graph = graph
        self.source = source
        self.target = target
        self.source_key_type = source_key_type
        self.target_key_type = target_key_type
        self.key_name = key_name
        self.attr = attr

        # Automatically calculate same_view, same_database, and same_server
        self.same_server = source.server == target.server
        self.same_database = self.same_server and source.database == target.database
        self.same_view = self.same_database and source.view == target.view

        # Create the edge in the graph
        self.edge = self.graph.add_edge(source.dd_for, target.dd_for,
                                        **self.attr)

        # Set edge attributes based on metadata
        self.graph.get_edge(source.dd_for,
                            target.dd_for).attr['label'] = key_name
        self.graph.get_edge(
            source.dd_for, target.dd_for
        ).attr['color'] = 'blue' if self.same_server else 'red'
        self.graph.get_edge(
            source.dd_for, target.dd_for
        ).attr['style'] = 'solid' if self.same_database else 'dashed'


# class TableEdge(pgv.Edge):
#     def __init__(self, graph: pgv.AGraph, source: 'TableNode', target: 'TableNode',
#                  source_key_type: str, target_key_type: str, key_name: str, **attr):
#         super().__init__(graph, source, target)
#         self.attr.update(attr)
#         self.source_key_type = source_key_type
#         self.target_key_type = target_key_type
#         self.key_name = key_name

#         # Automatically calculate same_view, same_database, and same_server
#         self.same_server = source.server == target.server
#         self.same_database = self.same_server and source.database == target.database
#         self.same_view = self.same_database and source.view == target.view

#         # Set edge attributes based on metadata
#         self.attr['label'] = key_name
#         self.attr['color'] = 'blue' if self.same_server else 'red'
#         self.attr['style'] = 'solid' if self.same_database else 'dashed'

# class TableNode(pgv.Node):
#     def __init__(self, graph: pgv.AGraph, dd_for: str, keys=[], url=None, **attr):
#         super().__init__(graph, dd_for)
#         self.attr.update(attr)

#         # Table naming convention: [server].[database].[view].[table]
#         names = dd_for[1:-1].split('].[') # Convert bracketed names to list
#         self.server = names[0]
#         self.database = names[1]
#         self.view = names[2]
#         self.table = names[3]

#         # Key information
#         self.keys = keys
#         self.url = url

#         # Set node attributes
#         self.attr['shape'] = 'box'
#         self.attr['style'] = 'filled'
#         self.attr['fillcolor'] = 'lightblue'
#         self.attr['label'] = f"{self.table}\n{', '.join(self.keys.keys())}"
#         if url:
#             self.attr['URL'] = url


def list_files(directory, extension=".xlsx"):
    path = Path(directory)
    return [
        str(file) for file in path.rglob(f'*{extension}') if file.is_file()
    ]


def load_json_data(file_paths):
    data = []
    for file_path in file_paths:
        if 'data_dict' not in file_path:
            continue
        json_str = dd_excel_to_json(file_path)
        data_dict = json.loads(json_str)
        data.append(data_dict)
    return data


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

    G = pgv.AGraph(strict=True, directed=False)

    # Dictionary to hold all field names, PK/UK/EK names and their respective tables
    field_dict = defaultdict(list)
    table_nodes = {}

    # Find all field names, UKs (UK or PK) and EKs and their respective tables
    for data_dict in json_data:
        table_name = data_dict['Data Dictionary For']
        keys = []
        for variable in data_dict['Variables']:
            if variable['Key Information'] == '':
                continue
            key_type = variable['Key Information'][0:2]
            if key_type not in ['PK', 'UK', 'EK', 'FK']:
                continue
            local_name = variable['Column Name']
            '''
            If the key information has a colon and a space, then the key maps to a different key name.
            The global name is the key name that the key maps to.
            '''
            if ': ' in variable['Key Information']:
                global_name = variable['Key Information'].split(': ')[1]
            else:
                global_name = local_name
            field_dict[global_name].append((table_name, local_name, key_type))
            key = Key(global_name, local_name, key_type)
            keys.append(key)
        node = TableNode(G, table_name, keys)
        table_nodes[table_name] = node
        # G.add_node(node)

    # Add edges to the graph
    for global_key, tables in field_dict.items():
        for table, _, key_type in tables:
            for other_table, _, other_key_type in field_dict[global_key]:
                if table != other_table:
                    source_node = table_nodes[table]
                    target_node = table_nodes[other_table]

                    edge = TableEdge(graph=G,
                                     source=source_node,
                                     target=target_node,
                                     source_key_type=key_type,
                                     target_key_type=other_key_type,
                                     key_name=global_key)
                    # G.add_edge(source_node, target_node, object=edge)

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
    files = list_files('RDMESSA')
    for file in files:
        if '.docx' in file:
            files.remove(file)
    # print(files)
    json_data = load_json_data(files)
    matching_fields = search_fields(json_data, ['ProgressCode'])
    if len(matching_fields) == 0:
        print('No matching fields found')
    for field in matching_fields:
        print(field)

    # G = build_graph(json_data)
    # G.layout(prog='dot')
    # G.draw('MDEORG.png')
    # for nodes in G.nodes():
    # print(nodes)
