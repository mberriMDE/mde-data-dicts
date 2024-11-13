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
def fiscal_to_school_year(year_int):
    year1 = str(year_int - 1)
    year2 = str(year_int)

    return f"{year1[2:]}-{year2[2:]}"


# Get column names excluding TimeID
query_columns = "SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'PSEOStudent' AND COLUMN_NAME != 'FiscalYear'"
columns = pd.read_sql(query_columns, conn)['COLUMN_NAME'].tolist()

# Query to get TimeID and all columns
query_data = "SELECT FiscalYear, " + ", ".join(
    columns) + " FROM dbo.PSEOStudent ORDER BY FiscalYear"
data = pd.read_sql(query_data, conn)

# Process each column to find introduced and last used years
school_years = []
for col in columns:
    non_null_years = data.loc[data[col].notna(), 'FiscalYear']

    if not non_null_years.empty:
        introduced_year = non_null_years.iloc[0]
        last_used_year = non_null_years.iloc[-1]

        introduced_school_year = fiscal_to_school_year(int(introduced_year))
        last_used_school_year = fiscal_to_school_year(int(last_used_year))

        school_years.append({
            'Column': col,
            'Introduced': introduced_school_year,
            'Last Used': last_used_school_year
        })

# Write to CSV
output_df = pd.DataFrame(school_years)
output_df.to_csv('column_school_years_fy.csv', index=False)

print("Results have been written to column_school_years_fy.csv")
