import database as db
import datajud
import json
import logging

# Config log
logging.basicConfig(level=logging.INFO)

# Get Token
token = db.get_config('datajud_token')
print(f"Token present: {bool(token)}")

# CNJ from screenshot
cnj = "08032859320258190031"

if token:
    print(f"Querying for {cnj}...")
    raw_data, error = datajud.consultar_processo(cnj, token)
    
    if error:
        print(f"Error: {error}")
    else:
        print("Success! Dumping raw structure keys...")
        print(f"Keys in root: {list(raw_data.keys())}")
        
        if 'partes' in raw_data:
            print(f"PARTES found (len={len(raw_data['partes'])})")
            print(json.dumps(raw_data['partes'], indent=2))
        else:
            print("PARTES NOT FOUND")
            
        if 'polos' in raw_data:
            print(f"POLOS found (len={len(raw_data['polos'])})")
            print(json.dumps(raw_data['polos'], indent=2))
        else:
            print("POLOS NOT FOUND")
            
        # Parse result
        parsed = datajud.parsear_dados(raw_data)
        print("\nParsed Result:")
        print(f"Partes count: {len(parsed['partes'])}")
        print(json.dumps(parsed['partes'], indent=2))
else:
    print("Token not found in DB config.")
