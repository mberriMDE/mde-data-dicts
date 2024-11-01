def get_col_headers(database_name):
    col_headers_dict = {
        'Typical': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information',
                'Reporting Cycle', 'Validations', 'Source Information'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'StudentLevelObservations': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'SIDataMart': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information',
                'Reporting Cycle'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'StudentLevelObservations': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'ESSA': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information',
                'Validations', 'Source Information'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'DIRS': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'Acceptable Values', 'Null Meaning',
                'Data Type', 'Max Characters', 'Notes', 'Key Information',
                'Source Information'
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        },
        'MDEORG': {
            'Legend': ['Data Dictionary Column Name', 'Description'],
            'Info and Uses': ['FAQ', 'Response'],
            'Relationships': [
                'Field Name in This Table', 'Relationship',
                'External Table Name', 'Field Name in External Table', 'Notes'
            ],
            'Data Dictionary': [
                'Field Name',
                'Description',
                'Reporting Status',
                'Introduced',
                'Discontinued',
                'Acceptable Values',
                'Null Meaning',
                'Data Type',
                'Max Characters',
                'Notes',
                'Key Information',
                'Reporting Cycle',
                'Validations',
                'Source Information',
                'Raw Data Origin',
            ],
            'Codes': [
                'Code', 'Description', 'Reporting Status', 'Introduced',
                'Discontinued', 'In Data', 'Notes'
            ]
        }
    }
    if database_name not in col_headers_dict:
        return col_headers_dict['Typical']
    else:
        return col_headers_dict[database_name]
