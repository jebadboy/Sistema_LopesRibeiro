import requests
from docx import Document
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH
from io import BytesIO
import pandas as pd
import PyPDF2
from datetime import datetime, timedelta
import re

# --- HELPERS DE FORMATAÇÃO E VALIDAÇÃO ---

def limpar_numeros(valor):
    """Remove tudo que não for dígito."""
    if not valor: return ""
    return re.sub(r'\D', '', str(valor))

def safe_float(val):
    """Converte para float de forma segura."""
    try:
        if isinstance(val, (int, float)): return float(val)
        if not val: return 0.0
        val = str(val).replace('R$', '').replace('.', '').replace(',', '.').strip()
        return float(val)
    except: return 0.0

def safe_int(val):
    """Converte para int de forma segura."""
    try: return int(float(val)) if val else 1
    except: return 1

def formatar_moeda(valor):
    """Formata float para moeda BRL."""
    try:
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except:
        return "R$ 0,00"

def formatar_documento(doc, tipo=None):
    """Formata CPF ou CNPJ."""
    if not doc:
        return ""
    d = limpar_numeros(doc)
    if len(d) == 11: # CPF
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    elif len(d) == 14: # CNPJ
        return f"{d[:2]}.{d[2:5]}.{d[5:8]}/{d[8:12]}-{d[12:]}"
    return doc

def formatar_cpf(cpf):
    """Formata CPF especificamente."""
    if not cpf:
        return ""
    d = limpar_numeros(cpf)
    if len(d) == 11:
        return f"{d[:3]}.{d[3:6]}.{d[6:9]}-{d[9:]}"
    return cpf

def formatar_celular(telefone):
    """Formata número de telefone brasileiro."""
    if not telefone:
        return ""
    d = limpar_numeros(str(telefone))
    if len(d) == 11:  # Celular com DDD
        return f"({d[:2]}) {d[2:7]}-{d[7:]}"
    elif len(d) == 10:  # Fixo com DDD
        return f"({d[:2]}) {d[2:6]}-{d[6:]}"
    return str(telefone)

def validar_cpf_matematico(cpf):
    """Valida CPF matematicamente."""
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

def validar_cnpj(cnpj):
    """Valida CNPJ matematicamente."""
    cnpj = limpar_numeros(cnpj)
    if len(cnpj) != 14: return False
    
    # Validação do primeiro dígito verificador
    pesos1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma1 = sum(int(cnpj[i]) * pesos1[i] for i in range(12))
    resto1 = soma1 % 11
    d1 = 0 if resto1 < 2 else 11 - resto1
    if d1 != int(cnpj[12]): return False
    
    # Validação do segundo dígito verificador
    pesos2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
    soma2 = sum(int(cnpj[i]) * pesos2[i] for i in range(13))
    resto2 = soma2 % 11
    d2 = 0 if resto2 < 2 else 11 - resto2
    return d2 == int(cnpj[13])

def validar_email(email):
    """Valida formato de email."""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, str(email).strip()))

def validar_telefone(telefone):
    """Valida número de telefone brasileiro."""
    if not telefone:
        return False
    d = limpar_numeros(telefone)
    
    # DDDs válidos no Brasil (11-99, exceto alguns)
    ddds_validos = [
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
        '98', '99'  # MA
    ]
    
    # Deve ter 10 ou 11 dígitos
    if len(d) not in [10, 11]:
        return False
    
    # Verifica DDD
    ddd = d[:2]
    if ddd not in ddds_validos:
        return False
    
    # Se tem 11 dígitos, deve ser celular (9 XXXX-XXXX)
    if len(d) == 11:
        if d[2] != '9':
            return False
    
    # Se tem 10 dígitos, deve ser fixo (não pode começar com 9)
    if len(d) == 10:
        if d[2] == '9':
            return False
    
    return True

def buscar_cep(cep):
    """Busca endereço pelo CEP usando API ViaCEP."""
    try:
        cep_limpo = limpar_numeros(cep)
        if len(cep_limpo) != 8:
            return None
        
        url = f"https://viacep.com.br/ws/{cep_limpo}/json/"
        response = requests.get(url, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "erro" not in data:
                return data
        return None
    except Exception as e:
        return None

# --- CÁLCULOS ---
def calcular_farol(d):
    try:
        delta = (datetime.strptime(d, '%Y-%m-%d').date() - datetime.now().date()).days
        if delta < 0: return "⚫ Vencido"
        return "🔴 Urgente" if delta <= 3 else "🟡 Atenção" if delta <= 7 else "🟢 No Prazo"
    except: return "⚪"

def calc_venc(d_ini, dias, tipo):
    if isinstance(d_ini, str): return None
    v = d_ini; c = 0
    if tipo == "Dias Corridos":
        v += timedelta(days=dias)
        while v.weekday() >= 5: v += timedelta(days=1)
    else:
        while c < dias:
            v += timedelta(days=1); 
            if v.weekday() < 5: c += 1
    return v

def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer: df.to_excel(writer, index=False)
    return output.getvalue()

def ler_pdf(file):
    txt = ""
    try:
        r = PyPDF2.PdfReader(file)
        for p in r.pages: txt += p.extract_text()
    except: return None
    return txt

# --- 📝 GERADOR DE DOCUMENTOS ---
def criar_doc(tipo, dados):
    doc = Document(); style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
    
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = p.add_run("SHEILA LOPES\nADVOGADA")
    run.bold = True
    run.font.size = Pt(12)
    doc.add_paragraph("\n")
    
    if tipo == "Proposta":
        t = doc.add_heading('PROPOSTA DE HONORÁRIOS', level=1)
        t.alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        obj = dados.get('proposta_objeto', 'Serviços Jurídicos')
        val_total = safe_float(dados.get('proposta_valor'))
        val_ent = safe_float(dados.get('proposta_entrada'))
        val_saldo = val_total - val_ent
        n_parc = safe_int(dados.get('proposta_parcelas'))
        forma = dados.get('proposta_pagamento', 'A Combinar')
        
        # Calcula valor da parcela
        v_parc = val_saldo / n_parc if n_parc > 0 else 0
        
        texto = f"""
Data: {datetime.now().strftime('%d/%m/%Y')}   Validade: 10 dias.

CONTRATANTE: {dados.get('nome', '').upper()}

1. OBJETO DOS SERVIÇOS:
{obj}

2. HONORÁRIOS (INVESTIMENTO):
Valor Total: {formatar_moeda(val_total)}.

3. CONDIÇÕES DE PAGAMENTO ({forma}):
a) ENTRADA: {formatar_moeda(val_ent)}, no ato da assinatura.
b) SALDO: {formatar_moeda(val_saldo)}, em {n_parc} parcelas de {formatar_moeda(v_parc)}.

4. SUCUMBÊNCIA:
Eventuais honorários de sucumbência pertencerão exclusivamente à Contratada.

Atenciosamente,
Dra. Sheila Lopes.
"""
    
    elif tipo == "Recibo":
        doc.add_heading('RECIBO', level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        txt = f"RECEBEMOS de {dados.get('cliente_nome', '').upper()}, a quantia de {formatar_moeda(dados.get('valor', 0))}, referente a {dados.get('descricao', '')}."
        texto = txt
        
    else:
        t_doc = "PROCURAÇÃO AD JUDICIA" if tipo=="Procuracao" else "CONTRATO DE HONORÁRIOS" if tipo=="Contrato" else "HIPOSSUFICIÊNCIA"
        doc.add_heading(t_doc, level=1).alignment = WD_ALIGN_PARAGRAPH.CENTER
        
        end_txt = f"{dados.get('endereco', '')}, {dados.get('numero_casa', '')}, {dados.get('complemento', '')}, {dados.get('bairro', '')}, {dados.get('cidade', '')}-{dados.get('estado', '')}, CEP {dados.get('cep', '')}"
        
        if tipo == "Contrato":
            obj = dados.get('proposta_objeto', 'Serviços Jurídicos')
            val = formatar_moeda(safe_float(dados.get('proposta_valor')))
            texto = f"CONTRATANTE: {dados.get('nome', '').upper()}, CPF/CNPJ {dados.get('cpf_cnpj', '')}.\nENDEREÇO: {end_txt}.\n\nOBJETO: {obj}.\nVALOR ACORDADO: {val}."
        else:
            texto = f"OUTORGANTE: {dados.get('nome', '').upper()}, nacionalidade brasileira, {dados.get('estado_civil', '')}, {dados.get('profissao', '')}, CPF/CNPJ {dados.get('cpf_cnpj', '')}, residente em {end_txt}."

    p_final = doc.add_paragraph(texto)
    p_final.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    
    doc.add_paragraph(f"\nMaricá/RJ, {datetime.now().strftime('%d/%m/%Y')}.\n\n")
    
    sig = doc.add_paragraph("__________________________________________________")
    sig.alignment = WD_ALIGN_PARAGRAPH.CENTER
    sig_nm = doc.add_paragraph(dados.get('nome', 'Lopes & Ribeiro').upper())
    sig_nm.alignment = WD_ALIGN_PARAGRAPH.CENTER

    b = BytesIO(); doc.save(b); b.seek(0); return b