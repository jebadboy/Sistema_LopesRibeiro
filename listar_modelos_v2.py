import google.generativeai as genai

# Chave fornecida pelo usuário
API_KEY = "AIzaSyAzDhyTwCbTVazjokfr0ut3yY1D25gOv24"

genai.configure(api_key=API_KEY)

print("Listando modelos disponíveis...")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            print(f"Nome: {m.name}")
            print(f"Display Name: {m.display_name}")
            print("-" * 20)
except Exception as e:
    print(f"Erro fatal: {e}")
