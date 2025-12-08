import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=api_key)

print("Testando Gemini 2.5 Flash Lite...")
try:
    model = genai.GenerativeModel('gemini-2.5-flash-lite')
    response = model.generate_content("Responda apenas: Funcionou!")
    print(f"Resposta: {response.text}")
except Exception as e:
    print(f"ERRO FATAL: {e}")
