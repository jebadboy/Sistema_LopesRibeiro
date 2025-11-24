import requests
import google.generativeai as genai
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import os
from dotenv import load_dotenv
import re
from datetime import timedelta, datetime
import pandas as pd
import PyPDF2
import streamlit as st

load_dotenv()
API_KEY_GEMINI = os.getenv("GOOGLE_API_KEY")

def limpar_numeros(valor):
    return ''.join(filter(str.isdigit, str(valor)))

def formatar_cpf(cpf):
    c = limpar_numeros(cpf)
    if len(c) == 11: return f"{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:]}"
    return cpf

def formatar_celular(tel):
    t = limpar_numeros(tel)
    if len(t) == 11: return f"({t[:2]}) {t[2:7]}-{t[7:]}" # Celular
    if len(t) == 10: return f"({t[:2]}) {t[2:6]}-{t[6:]}" # Fixo
    return tel

def formatar_link_zap(tel):
    """Gera o link para abrir o WhatsApp"""
    t = limpar_numeros(tel)
    if not t: return None
    return f"https://wa.me/55{t}"

def formatar_moeda(v): 
    try: return f"R$ {float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except: return "R$ 0,00"

# --- VALIDADORES LÓGICOS ---
def validar_cpf_matematico(cpf):
    cpf = limpar_numeros(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11: return False
    soma = sum(int(cpf[i]) * (10 - i) for i in range(9))
    resto = (soma * 10) % 11
    d1 = 0 if resto == 10 else resto
    if d1 != int(cpf[9]): return False
    soma = sum(int(cpf[i]) * (11 - i) for i in range(10))
    resto = (soma * 10) % 11
    d2 = 0 if resto == 10 else resto
    return d2 == int(cpf[10])

def validar_email(email):
    """Valida formato de email usando regex."""
    if not email: return False
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# DDDs válidos do Brasil (principais)
DDDs_VALIDOS = [
    '11', '12', '13', '14', '15', '16', '17', '18', '19',  # SP
    '21', '22', '24',  # RJ
    '27', '28',  # ES
    '31', '32', '33', '34', '35', '37', '38',  # MG
    '41', '42', '43', '44', '45', '46',  # PR
    '47', '48', '49',  # SC
    '51', '53', '54', '55',  # RS
    '61',  # DF
    '62', '64',  # GO
    '63',  # TO
    '65', '66',  # MT
    '67',  # MS
    '68',  # AC
    '69',  # RO
    '71', '73', '74', '75', '77',  # BA
    '79',  # SE
    '81', '87',  # PE
    '82',  # AL
    '83',  # PB
    '84',  # RN
    '85', '88',  # CE
    '86', '89',  # PI
    '91', '93', '94',  # PA
    '92', '97',  # AM
    '95',  # RR
    '96',  # AP
    '98', '99'   # MA
]

def validar_telefone(telefone):
    """Valida telefone brasileiro (celular ou fixo) com verificação de DDD."""
    numeros = limpar_numeros(telefone)
    if len(numeros) not in [10, 11]:
        return False
    
    # Validar DDD
    ddd = numeros[:2]
    if ddd not in DDDs_VALIDOS:
        return False
    
    if len(numeros) == 11:  # Celular: (XX) 9XXXX-XXXX
        return numeros[2] == '9'  # Terceiro dígito deve ser 9
    elif len(numeros) == 10:  # Fixo: (XX) XXXX-XXXX
        return numeros[2] != '9'  # Terceiro dígito não deve ser 9
    return False

@st.cache_data(ttl=3600)  # Cache por 1 hora
def buscar_cep(cep): 
    """Busca CEP via API ViaCEP com cache de 1 hora."""
    try: 
        response = requests.get(f"https://viacep.com.br/ws/{limpar_numeros(cep)}/json/", timeout=5)
        return response.json()
    except requests.Timeout:
        return {"erro": "timeout"}
    except: 
        return None

def calc_venc(data_pub, dias, regra):
    """Calcula vencimento somando dias à data de publicação."""
    # Por enquanto, usa apenas dias corridos (melhoria futura: dias úteis com feriados)
    if regra == "Dias Úteis":
        # Implementação simplificada - não considera feriados
        contador = 0
        data_atual = data_pub
        while contador < dias:
            data_atual += timedelta(days=1)
            if data_atual.weekday() < 5:  # Segunda a Sexta = 0-4
                contador += 1
        return data_atual
    else:  # Corridos
        return data_pub + timedelta(days=dias)

def calcular_farol(prazo):
    """Retorna emoji de farol baseado na proximidade do prazo."""
    try:
        if isinstance(prazo, str):
            prazo = datetime.strptime(prazo, "%Y-%m-%d")
        dias_restantes = (prazo - datetime.now()).days
        if dias_restantes < 0: return "🔴"  # Vencido
        elif dias_restantes < 5: return "🟡"  # Urgente
        else: return "🟢"  # Normal
    except:
        return "⚪"  # Erro ou data inválida

# --- AUXILIARES ---
def safe_float(val):
    try: return float(val) if val else 0.0
    except: return 0.0

def safe_int(val):
    try: return int(float(val)) if val else 1
    except: return 1

def to_excel(df):
    """Converte DataFrame para Excel em bytes (para download)."""
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Dados')
    return output.getvalue()

# --- GERADORES (IA, PDF, WORD) ---
def obter_modelo_ativo():
    try:
        genai.configure(api_key=API_KEY_GEMINI)
        return 'gemini-flash-latest'
    except: return 'gemini-flash-latest'

def consultar_ia(prompt):
    if API_KEY_GEMINI:
        try:
            genai.configure(api_key=API_KEY_GEMINI)
            model = genai.GenerativeModel('gemini-flash-latest') 
            return model.generate_content(prompt).text
        except Exception as e: return f"Erro IA: {str(e)}"
    else: return "⚠️ Sem Chave API configurada no secrets.toml"

def ler_pdf(file):
    txt = ""
    try:
        r = PyPDF2.PdfReader(file)
        for p in r.pages: txt += p.extract_text()
    except: return None
    return txt

def criar_doc(tipo, dados):
    doc = Document(); style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER; run = p.add_run("SHEILA LOPES\\nADVOGADA"); run.bold = True
    doc.add_paragraph("\\n")
    
    if tipo == "Proposta":
        t = doc.add_heading('PROPOSTA DE HONORÁRIOS', level=1); t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        obj = dados.get('proposta_objeto', 'Ação Judicial')
        val_tot = formatar_moeda(safe_float(dados.get('proposta_valor')))
        entrada = formatar_moeda(safe_float(dados.get('proposta_entrada')))
        saldo = formatar_moeda(safe_float(dados.get('proposta_valor')) - safe_float(dados.get('proposta_entrada')))
        parc = safe_int(dados.get('proposta_parcelas'))
        forma = dados.get('proposta_pagamento', 'A Combinar')
        texto = f"""Data: {datetime.now().strftime('%d/%m/%Y')}   Validade: 10 dias.\\n\\nCONTRATANTE: {dados['nome'].upper()}\\n\\n1. OBJETO:\\n{obj}\\n\\n2. INVESTIMENTO:\\nValor Total: {val_tot}\\n\\n3. PAGAMENTO ({forma}):\\n- Entrada: {entrada}\\n- Saldo: {saldo}, em {parc}x mensais.\\n\\n4. SUCUMBÊNCIA:\\nExclusivos da Contratada.\\n\\nAtenciosamente,\\nDra. Sheila Lopes."""
    elif tipo == "Recibo":
        doc.add_heading('RECIBO', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        val = formatar_moeda(safe_float(dados.get('valor', 0)))
        desc = dados.get('descricao', '')
        nome_cliente = dados.get('cliente_nome', '')
        texto = f"Recebi de {nome_cliente}, a quantia de {val}, referente a {desc}.\\n\\nPor ser verdade, firmo o presente."
    else:
        t_doc = "PROCURAÇÃO" if tipo=="Procuracao" else "CONTRATO" if tipo==" Contrato" else "HIPOSSUFICIÊNCIA"
        doc.add_heading(t_doc, level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        end_txt = f"{dados['endereco']}, {dados['numero_casa']}, {dados['complemento']}, {dados['bairro']}, {dados['cidade']}-{dados['estado']}, CEP {dados['cep']}"
        if tipo == "Contrato":
            obj = dados.get('proposta_objeto', 'Serviços Jurídicos')
            val = formatar_moeda(safe_float(dados.get('proposta_valor')))
            texto = f"CONTRATANTE: {dados['nome'].upper()}, CPF {dados['cpf_cnpj']}.\\nENDEREÇO: {end_txt}.\\n\\nOBJETO: {obj}.\\nVALOR: {val}."
        else:
            texto = f"OUTORGANTE: {dados['nome'].upper()}, nacionalidade brasileira, {dados['estado_civil']}, {dados['profissao']}, CPF {dados['cpf_cnpj']}, residente em {end_txt}."

    doc.add_paragraph(texto).alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.add_paragraph(f"\\nMaricá, {datetime.now().strftime('%d/%m/%Y')}.\\n\\n______________________\\nAssinatura")
    b = BytesIO(); doc.save(b); b.seek(0); return b