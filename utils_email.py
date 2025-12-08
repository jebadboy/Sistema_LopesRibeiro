
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import database as db
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def enviar_email(destinatario, assunto, corpo_html):
    """
    Envia um e-mail HTML usando as configurações SMTP do banco.
    Retorna (True, None) em caso de sucesso ou (False, erro) em falha.
    """
    try:
        # Obter configurações
        smtp_server = db.get_config('smtp_server')
        smtp_port = db.get_config('smtp_port')
        smtp_user = db.get_config('smtp_email')
        smtp_pass = db.get_config('smtp_password')
        
        if not all([smtp_server, smtp_port, smtp_user, smtp_pass]):
            return False, "Configurações de SMTP incompletas. Contate o administrador."
            
        # Configurar mensagem
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = destinatario
        msg['Subject'] = assunto
        
        msg.attach(MIMEText(corpo_html, 'html'))
        
        # Conectar e enviar
        # Tenta usar SSL na porta 465 ou TLS na 587
        if str(smtp_port) == '465':
            server = smtplib.SMTP_SSL(smtp_server, int(smtp_port))
        else:
            server = smtplib.SMTP(smtp_server, int(smtp_port))
            server.starttls()
            
        server.login(smtp_user, smtp_pass)
        server.sendmail(smtp_user, destinatario, msg.as_string())
        server.quit()
        
        logger.info(f"Email enviado com sucesso para {destinatario}")
        return True, None
        
    except Exception as e:
        logger.error(f"Erro ao enviar email para {destinatario}: {e}")
        return False, str(e)

def enviar_codigo_recuperacao(destinatario, codigo):
    """Envia o código de recuperação de senha"""
    template = f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background-color: #0f172a; padding: 20px; text-align: center;">
            <h2 style="color: #fff; margin: 0;">Lopes & Ribeiro</h2>
        </div>
        <div style="padding: 30px;">
            <h3 style="color: #0f172a; margin-top: 0;">Recuperação de Senha</h3>
            <p>Recebemos uma solicitação para redefinir a senha da sua conta.</p>
            <p>Seu código de recuperação é:</p>
            <div style="background-color: #f1f5f9; font-size: 24px; font-weight: bold; padding: 15px; text-align: center; letter-spacing: 5px; border-radius: 6px; margin: 20px 0;">
                {codigo}
            </div>
            <p>Este código expira em 15 minutos.</p>
            <p style="font-size: 0.9em; color: #666;">Se você não solicitou esta alteração, ignore este e-mail.</p>
        </div>
        <div style="background-color: #f8fafc; padding: 15px; text-align: center; font-size: 0.8em; color: #94a3b8;">
            &copy; {datetime.now().year} Lopes & Ribeiro Advogados Associados
        </div>
    </div>
    """
    
    return enviar_email(destinatario, "Código de Recuperação de Senha", template)
