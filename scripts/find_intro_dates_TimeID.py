import pyodbc
import pandas as pd

# Set up database connection
server_name = 'E60SDWP20WDB001'
database_name = 'SLEDSDW'
connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server_name};DATABASE={database_name};Trusted_Connection=yes;"
try:
    conn = pyodbc.connect(connection_string)
except Exception as e:
    print("Error in connection: ", e)


# Helper function to convert YYYYMMDD to school year format
def date_to_school_year(date_int):
    year = date_int // 10000
    month = (date_int // 100) % 100
    if month >= 5:  # School year (summer) starts in May
        return f"{str(year)[2:]}-{str(year + 1)[2:]}"
    else:
        return f"{str(year - 1)[2:]}-{str(year)[2:]}"


def last_date_to_school_year(date_int):
    year = date_int // 10000
    month = (date_int // 100) % 100
    if month >= 7:  # School year starts in July
        return f"{str(year)[2:]}-{str(year + 1)[2:]}"
    else:
        return f"{str(year - 1)[2:]}-{str(year)[2:]}"


# Get column names excluding TimeID
query_columns = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'PSEnrollment' AND COLUMN_NAME != 'TimeID'"
columns = pd.read_sql(query_columns, conn)['COLUMN_NAME'].tolist()

# Query to get TimeID and all columns
query_data = "SELECT TimeID, " + ", ".join(
    columns) + " FROM dbo.PSEnrollment ORDER BY TimeID"
data = pd.read_sql(query_data, conn)

# Process each column to find introduced and last used years
school_years = []
for col in columns:
    non_null_dates = data.loc[data[col].notna(), 'TimeID']

    if not non_null_dates.empty:
        introduced_date = non_null_dates.iloc[0]
        last_used_date = non_null_dates.iloc[-1]

        introduced_school_year = date_to_school_year(int(introduced_date))
        last_used_school_year = date_to_school_year(int(last_used_date))

        school_years.append({
            'Column': col,
            'Introduced': introduced_school_year,
            'Last Used': last_used_school_year
        })

# Write to CSV
output_df = pd.DataFrame(school_years)
output_df.to_csv('column_school_years.csv', index=False)

print("Results have been written to column_school_years.csv")
