import utils
import database
import pandas as pd

print("Imports successful.")

# Check utils
try:
    # Just check if function exists
    if hasattr(utils, 'gerar_documento'):
        print("utils.gerar_documento exists.")
    else:
        print("FAIL: utils.gerar_documento missing.")
    
    if hasattr(utils, 'criar_doc'):
        print("utils.criar_doc exists.")
    else:
        print("FAIL: utils.criar_doc missing.")

except Exception as e:
    print(f"utils check failed: {e}")

# Check database connection
try:
    with database.get_connection() as conn:
        print("database connection successful.")
except Exception as e:
    print(f"database connection failed: {e}")

# Check sql_get validation
try:
    database.sql_get("clientes", "id; DROP TABLE clientes")
    print("FAIL: sql_get did not raise error for injection.")
except ValueError as e:
    print(f"SUCCESS: sql_get raised error for injection: {e}")
except Exception as e:
    print(f"sql_get raised unexpected error: {e}")

# Check database functions
try:
    if hasattr(database, 'get_usuario_by_username'):
        print("database.get_usuario_by_username exists.")
    else:
        print("FAIL: database.get_usuario_by_username missing.")

    if hasattr(database, 'get_config'):
        print("database.get_config exists.")
    else:
        print("FAIL: database.get_config missing.")

except Exception as e:
    print(f"database function check failed: {e}")

print("Verification complete.")
