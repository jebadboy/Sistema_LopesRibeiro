import os
import datetime
from google_calendar import autenticar_google

def debug_calendar():
    print("--- INICIANDO DEBUG GOOGLE CALENDAR ---")
    
    # 1. Tentar autenticar
    username = "admin" # Assumindo admin ou o usuário padrão
    print(f"Tentando autenticar como: {username}")
    
    service = autenticar_google(username)
    
    if not service:
        print("❌ Falha na autenticação. Verifique credentials.json e token.")
        return

    print("✅ Autenticação bem sucedida!")

    # 2. Listar Calendários
    print("\n--- LISTA DE CALENDÁRIOS DISPONÍVEIS ---")
    try:
        calendar_list = service.calendarList().list().execute()
        calendars = calendar_list.get('items', [])
        
        if not calendars:
            print("⚠️ Nenhum calendário encontrado.")
        
        for calendar in calendars:
            print(f"ID: {calendar['id']}")
            print(f"Resumo: {calendar.get('summary', 'Sem título')}")
            print(f"Primário: {calendar.get('primary', False)}")
            print("-" * 30)
            
    except Exception as e:
        print(f"❌ Erro ao listar calendários: {e}")

    # 3. Listar Próximos 10 Eventos do Primário
    print("\n--- PRÓXIMOS 10 EVENTOS (CALENDÁRIO PRIMÁRIO) ---")
    try:
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        print(f"Buscando eventos a partir de: {now}")
        
        events_result = service.events().list(
            calendarId='primary', 
            timeMin=now,
            maxResults=10, 
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])

        if not events:
            print("⚠️ Nenhum evento futuro encontrado no calendário primário.")
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"Evento: {event['summary']} | Início: {start}")
                
    except Exception as e:
        print(f"❌ Erro ao listar eventos: {e}")

if __name__ == "__main__":
    debug_calendar()
