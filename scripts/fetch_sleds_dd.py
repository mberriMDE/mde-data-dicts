import requests
import csv

# Base URLs
variables_url = 'https://sleds.mn.gov/ibi_apps/WFServlet'
variable_detail_url = 'https://sleds.mn.gov/ibi_apps/WFServlet'

# Parameters to get all variables
params = {
    'IBIF_ex': 'sledsws_getdata_dd_variable_list.fex',
    'dataDictionaryAToZ': '_FOC_NULL',
    'dataDictionaryCkBoxVar': 1,
    'dataDictionaryCkBoxVarLabel': 1,
    'dataDictionaryCkBoxDescription': 'true',
    'dataDictionaryCkBoxCodes': 'true'
}

# Use a session to reuse connections
session = requests.Session()

# Fetch the list of variables
response = session.get(variables_url, params=params)
response.encoding = 'utf-8'

if response.status_code == 200:
    data = response.json()
    variables = data['variables']

    # Filter variables for 'ABEParticipation' table
    abe_variables = [
        var for var in variables if var.get('SLEDSTable') == 'ABEParticipation'
    ]

    if not abe_variables:
        print('No variables found for the ABEParticipation table.')
    else:
        total_variables = len(abe_variables)
        print(
            f'Found {total_variables} variables for the ABEParticipation table.'
        )

        with open('abe_variable_details.csv',
                  'w',
                  newline='',
                  encoding='utf-8') as csvfile:
            fieldnames = [
                'variable', 'variableLabel', 'definition', 'elementId',
                'validYears', 'numberOfCodes'
            ]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()

            for idx, variable in enumerate(abe_variables):
                print(
                    f'Processing {idx+1}/{total_variables}: {variable["variable"]}'
                )
                elementId = variable['elementId']

                # Parameters to get variable details
                detail_params = {
                    'IBIF_ex': 'sledsws_getdata_dd_variable_detail.fex',
                    'dataDictionaryElementId': elementId
                }

                try:
                    detail_response = session.get(variable_detail_url,
                                                  params=detail_params,
                                                  timeout=10)
                    detail_response.encoding = 'utf-8'

                    if detail_response.status_code == 200:
                        detail_data = detail_response.json()
                        detail_variables = detail_data.get('variables', [])
                        if detail_variables:
                            detail = detail_variables[0]
                            # Write variable name and details to CSV
                            writer.writerow({
                                'variable':
                                detail.get('variable', ''),
                                'variableLabel':
                                detail.get('variableLabel', ''),
                                'definition':
                                detail.get('definition', ''),
                                'elementId':
                                detail.get('elementId', ''),
                                'validYears':
                                detail.get('validYears', ''),
                                'numberOfCodes':
                                detail.get('numberOfCodes', '')
                            })
                        else:
                            print(
                                f'No details found for elementId {elementId}')
                    else:
                        print(
                            f'Error fetching details for elementId {elementId}: {detail_response.status_code}'
                        )
                except requests.exceptions.Timeout:
                    print(f'Timeout occurred for elementId {elementId}')
                except Exception as e:
                    print(f'An error occurred for elementId {elementId}: {e}')
else:
    print('Error fetching variables:', response.status_code)
