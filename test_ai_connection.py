import utils as ut
import os

print("--- Testing utils.py Fixes ---")

# Test 1: Check API Key
print(f"API Key Loaded: {bool(ut.API_KEY_GEMINI)}")
if ut.API_KEY_GEMINI:
    print(f"API Key Prefix: {ut.API_KEY_GEMINI[:5]}...")
else:
    print("ERROR: API Key is None or Empty")

# Test 2: Check limpar_numeros
test_val = "123.456.789-00"
expected = "12345678900"
result = ut.limpar_numeros(test_val)
print(f"limpar_numeros('{test_val}') = '{result}'")

if result == expected:
    print("limpar_numeros: SUCCESS")
else:
    print(f"limpar_numeros: FAILED (Expected '{expected}', got '{result}')")

# Test 3: Check AI Connection (Optional, but good to check if key is valid)
print("\n--- Testing AI Connection ---")
try:
    response = ut.consultar_ia("Hello, are you working?")
    print(f"AI Response: {response[:50]}...")
    print("AI Connection: SUCCESS")
except Exception as e:
    print(f"AI Connection: FAILED ({e})")
