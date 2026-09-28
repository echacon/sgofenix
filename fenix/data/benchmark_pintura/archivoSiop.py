import pandas as pd
import pyodbc

# Conectar a SQL Server
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=localhost\\SQLEXPRESS;'
    'DATABASE=SiopDB;'
    'Trusted_Connection=yes;'
)

# Consulta para listar todas las tablas
query_tablas = """
SELECT 
    TABLE_NAME 
FROM INFORMATION_SCHEMA.TABLES 
WHERE TABLE_TYPE = 'BASE TABLE'
ORDER BY TABLE_NAME
"""

# Obtener lista de tablas
tablas_df = pd.read_sql(query_tablas, conn)

print("📋 Tablas en la base de datos SiopDB:")
print(tablas_df)

conn.close()