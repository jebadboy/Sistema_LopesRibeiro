import io
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
import database as db

try:
    from num2words import num2words
except ImportError:
    num2words = None

def valor_por_extenso(valor):
    """Gera o valor por extenso em reais."""
    if num2words:
        try:
            return num2words(valor, lang='pt_BR', to='currency')
        except:
            return f"R$ {valor:,.2f}"
    return f"R$ {valor:,.2f}"

def gerar_recibo_pdf(dados):
    """
    Gera um recibo em PDF.
    dados = {
        'nome_cliente': str,
        'cpf_cliente': str,
        'valor': float,
        'descricao': str,
        'data': datetime (obj or str)
    }
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # Configurações do Escritório
    nome_escritorio = db.get_config('nome_escritorio', 'Lopes & Ribeiro Advogados')
    oab = db.get_config('oab', '')
    endereco = db.get_config('endereco_escritorio', '')
    cnpj = db.get_config('cnpj_escritorio', '') # Caso tenha
    
    # --- CABEÇALHO ---
    y = height - 3*cm
    
    # Logo (se existir)
    logo_path = "LOGO.jpg"
    if os.path.exists(logo_path):
        try:
            c.drawImage(logo_path, 2*cm, y-1*cm, width=3*cm, preserveAspectRatio=True, mask='auto')
        except:
            pass
            
    # Dados do Escritório (Centralizado ou à direita do logo)
    c.setFont("Helvetica-Bold", 14)
    c.drawString(6*cm, y, nome_escritorio)
    
    c.setFont("Helvetica", 10)
    c.drawString(6*cm, y-0.6*cm, f"{oab}")
    c.drawString(6*cm, y-1.1*cm, f"{endereco}")
    if cnpj:
        c.drawString(6*cm, y-1.6*cm, f"CNPJ: {cnpj}")
        
    # Linha divisória
    c.setLineWidth(1)
    c.line(2*cm, y-2.5*cm, width-2*cm, y-2.5*cm)
    
    # --- TÍTULO ---
    y -= 4.5*cm
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(width/2, y, "RECIBO DE PAGAMENTO DE HONORÁRIOS")
    
    # --- CORPO ---
    y -= 3*cm
    c.setFont("Helvetica", 12)
    
    texto_valor = valor_por_extenso(dados['valor'])
    
    # Montagem do texto
    # Usando textObject para melhor controle ou desenhando linha a linha
    
    margin_left = 2.5*cm
    line_height = 0.8*cm
    
    c.drawString(margin_left, y, f"Recebemos de: {dados['nome_cliente']}")
    y -= line_height
    c.drawString(margin_left, y, f"CPF/CNPJ: {dados['cpf_cliente']}")
    y -= line_height
    
    c.drawString(margin_left, y, f"A importância de: R$ {dados['valor']:,.2f} ({texto_valor})")
    y -= line_height
    
    c.drawString(margin_left, y, f"Referente a: {dados['descricao']}")
    y -= line_height
    
    data_pag = dados.get('data', datetime.now())
    if isinstance(data_pag, str):
        try:
            data_pag = datetime.strptime(data_pag, '%Y-%m-%d')
        except:
            data_pag = datetime.now()
            
    c.drawString(margin_left, y, f"Data do Pagamento: {data_pag.strftime('%d/%m/%Y')}")
    
    # --- ASSINATURA (Logo após o corpo) ---
    y -= 3 * line_height  # 3 linhas após a data
    
    # Cidade e Data
    c.setFont("Helvetica", 11)
    c.drawCentredString(width/2, y, f"Maricá/RJ, {datetime.now().strftime('%d de %B de %Y')}")
    
    y -= 2*cm
    c.line(width/2 - 4*cm, y, width/2 + 4*cm, y)
    c.setFont("Helvetica-Oblique", 10)
    c.drawCentredString(width/2, y-0.5*cm, nome_escritorio)
    c.drawCentredString(width/2, y-1.0*cm, "Assinatura Digital")

    # --- RODAPÉ (Fixo no fim da página) ---
    y_footer = 2.0 * cm # Margem inferior fixa
    
    # Contatos no Rodapé
    email = db.get_config('email_escritorio', '')
    telefone = db.get_config('telefone_escritorio', '')
    
    if email or telefone:
        c.setFont("Helvetica", 9)
        contato_texto = []
        if email: contato_texto.append(email)
        if telefone: contato_texto.append(telefone)
        c.drawCentredString(width/2, y_footer, " | ".join(contato_texto))
    
    c.save()
    buffer.seek(0)
    return buffer
