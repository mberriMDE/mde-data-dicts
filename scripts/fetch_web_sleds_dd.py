import requests
import json
import re

# URL for the variables list endpoint
url = "https://sleds.mn.gov/ibi_apps/WFServlet"

variable_ibif = 'sledsws_getdata_dd_variable_list.fex'
'''
json structure:
{"errorMessage":null,"variables":[{"variable":"ABEIndicator","elementId":3810,"variableLabel":"ABEIndicator","SLEDSTable":"MCCCScheduleCourseDimension","formattedNumberOfCodes":"2","validYears":"2017-Present"}
,{"variable":"ABEOrganizationID","elementId":1446,"variableLabel":"ABE Organization ID","SLEDSTable":"ABEParticipation","formattedNumberOfCodes":"","validYears":"1979-Present"}
'''

detail_ibif = 'sledsws_getdata_dd_variable_detail.fex',
'''
json structure:
{"errorMessage":null,"variables":[{"variable":"Zipcode","elementId":3881,"variableLabel":"Zipcode","tableLink":"PSEnrollment","formattedNumberOfCodes":"1","validYears":"2016-Present"
,"definition":"Actual Zip Code"}]}
'''

codes_ibif = 'sledsws_getdata_dd_variable_codes.fex',
#    'dataDictionaryElementId': '3881',
'''
json structure:
{"errorMessage":null,"elementId": 3881,"codes":[{"code":"99999","definition":"Unknown","longDefinition":"Zip code unknown","validYears":"2016-Present"}]}
'''

# session = requests.Session()
# code_params = {'IBIF_ex': codes_ibif, 'dataDictionaryElementId': '153'}
# variable_params = {'IBIF_ex': variable_ibif}

# response = session.get(url, params=code_params)
# response.encoding = 'utf-8'
# print(response.text)

fetched_data = {}
# Use a session to make multiple requests
with requests.Session() as session:
    # Fetch the list of variables
    variable_params = {'IBIF_ex': variable_ibif}
    response = session.get(url, params=variable_params)
    response.encoding = 'utf-8'

    if response.status_code == 200:
        data = response.json()
        variables = data['variables']
        for var in variables:
            fetched_data[var['elementId']] = {
                'variable_name': var['variable'].lower(),
                'table_name': var['SLEDSTable'].lower(),
                'number_of_codes': var['formattedNumberOfCodes']
            }
    else:
        print('Error fetching variables:', response.status_code)

    # Fetch the details and codes for each variable
    for var_id in fetched_data.keys():
        detail_params = {
            'IBIF_ex': detail_ibif,
            'dataDictionaryElementId': var_id
        }
        detail_response = session.get(url, params=detail_params)
        detail_response.encoding = 'utf-8'

        if detail_response.status_code == 200:
            clean_detail_text = re.sub(
                r'[\x00-\x1F\x7F-\x9F]', '',
                detail_response.text)  # Remove control characters
            detail_data = json.loads(clean_detail_text)
            fetched_data[var_id]['description'] = detail_data['variables'][0][
                'definition']
        else:
            print('Error fetching variable details:',
                  detail_response.status_code)

        codes_params = {
            'IBIF_ex': codes_ibif,
            'dataDictionaryElementId': var_id
        }
        codes_response = session.get(url, params=codes_params)
        codes_response.encoding = 'utf-8'

        if codes_response.status_code == 200:
            clean_codes_text = re.sub(
                r'[\x00-\x1F\x7F-\x9F]', '',
                codes_response.text)  # Remove control characters
            # Escape all unescaped backslashes
            escaped_text = re.sub(r'\\(?!["\\/bfnrtu])', r'\\\\',
                                  clean_codes_text)
            try:
                codes_data = json.loads(escaped_text)
                if fetched_data[var_id]['number_of_codes'] != '':
                    fetched_data[var_id]['codes'] = codes_data['codes']
            except json.JSONDecodeError:
                print('Error decoding JSON:', clean_codes_text)

        else:
            print('Error fetching variable codes:', codes_response.status_code)

# Change the key from elementId to {SLEDSTable}.{variable_name}
final_data = {}
for key, value in fetched_data.items():
    table = value['table_name']
    if table not in final_data:
        final_data[table] = {}

    variable = value['variable_name']
    final_data[table][variable] = value

# save the fetched data to a JSON file
import json

with open('fetched_data.json', 'w') as f:
    json.dump(final_data, f, indent=4)
