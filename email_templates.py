"""
Templates de E-mail Transacionais
Sistema Lopes & Ribeiro

Contém templates HTML para:
- Boas-vindas a novo cliente
- Lembrete de pagamento (cobrança)
- Parabéns de aniversário
- Atualização de processo
"""

from datetime import datetime


def _base_template(titulo: str, conteudo: str) -> str:
    """Template base com header e footer padrão."""
    ano = datetime.now().year
    return f"""
    <div style="font-family: Arial, sans-serif; color: #333; max-width: 600px; margin: 0 auto; border: 1px solid #ddd; border-radius: 8px; overflow: hidden;">
        <div style="background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); padding: 25px; text-align: center;">
            <h2 style="color: #fff; margin: 0; font-size: 24px;">⚖️ Lopes & Ribeiro</h2>
            <p style="color: #94a3b8; margin: 5px 0 0 0; font-size: 14px;">Advogados Associados</p>
        </div>
        <div style="padding: 30px;">
            <h3 style="color: #0f172a; margin-top: 0; border-bottom: 2px solid #3b82f6; padding-bottom: 10px;">
                {titulo}
            </h3>
            {conteudo}
        </div>
        <div style="background-color: #f8fafc; padding: 20px; text-align: center; font-size: 0.85em; color: #64748b;">
            <p style="margin: 0;">Este é um e-mail automático do Sistema Lopes & Ribeiro.</p>
            <p style="margin: 5px 0 0 0;">&copy; {ano} Lopes & Ribeiro Advogados Associados</p>
        </div>
    </div>
    """


def template_boas_vindas(nome_cliente: str, telefone_escritorio: str = "(21) 99999-9999") -> str:
    """
    Template de boas-vindas para novo cliente.
    
    Args:
        nome_cliente: Nome do cliente
        telefone_escritorio: Telefone de contato do escritório
    """
    conteudo = f"""
    <p>Olá, <strong>{nome_cliente}</strong>!</p>
    
    <p>É com grande satisfação que damos as boas-vindas ao escritório <strong>Lopes & Ribeiro Advogados Associados</strong>.</p>
    
    <p>A partir de agora, você conta com uma equipe jurídica dedicada a defender seus interesses com ética, competência e transparência.</p>
    
    <div style="background-color: #f1f5f9; padding: 15px; border-radius: 6px; margin: 20px 0;">
        <p style="margin: 0; font-weight: bold;">📋 Próximos Passos:</p>
        <ul style="margin: 10px 0;">
            <li>Reunir a documentação necessária para seu caso</li>
            <li>Aguardar contato do advogado responsável</li>
            <li>Em caso de dúvidas, entre em contato conosco</li>
        </ul>
    </div>
    
    <p>📞 <strong>Contato:</strong> {telefone_escritorio}</p>
    
    <p>Atenciosamente,<br/>
    <strong>Equipe Lopes & Ribeiro</strong></p>
    """
    return _base_template("Bem-vindo(a)!", conteudo)


def template_lembrete_pagamento(
    nome_cliente: str, 
    descricao: str, 
    valor: float, 
    vencimento: str,
    dias_atraso: int = 0
) -> str:
    """
    Template de lembrete de pagamento / cobrança.
    
    Args:
        nome_cliente: Nome do cliente
        descricao: Descrição do lançamento
        valor: Valor devido
        vencimento: Data de vencimento formatada
        dias_atraso: Dias em atraso (0 se for lembrete preventivo)
    """
    status_cor = "#ef4444" if dias_atraso > 0 else "#f59e0b"
    status_texto = f"⚠️ <strong>{dias_atraso} dias em atraso</strong>" if dias_atraso > 0 else "📅 Vencimento próximo"
    
    conteudo = f"""
    <p>Prezado(a) <strong>{nome_cliente}</strong>,</p>
    
    <p>Gostaríamos de lembrar sobre o seguinte compromisso financeiro:</p>
    
    <div style="background-color: #f1f5f9; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid {status_cor};">
        <p style="margin: 0 0 10px 0; color: {status_cor};">{status_texto}</p>
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Descrição:</td>
                <td style="padding: 8px 0; font-weight: bold;">{descricao}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Valor:</td>
                <td style="padding: 8px 0; font-weight: bold; font-size: 1.2em; color: #0f172a;">R$ {valor:,.2f}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">Vencimento:</td>
                <td style="padding: 8px 0; font-weight: bold;">{vencimento}</td>
            </tr>
        </table>
    </div>
    
    <p>Para sua comodidade, oferecemos as seguintes formas de pagamento:</p>
    <ul>
        <li><strong>PIX</strong> - Chave a ser informada pelo escritório</li>
        <li><strong>Transferência Bancária</strong> - Dados fornecidos pelo escritório</li>
    </ul>
    
    <p>Em caso de dúvidas ou se já efetuou o pagamento, por favor, desconsidere este e-mail e entre em contato conosco.</p>
    
    <p>Atenciosamente,<br/>
    <strong>Setor Financeiro - Lopes & Ribeiro</strong></p>
    """
    return _base_template("Lembrete de Pagamento", conteudo)


def template_aniversario(nome_cliente: str, idade: int = None) -> str:
    """
    Template de parabéns de aniversário.
    
    Args:
        nome_cliente: Nome do cliente
        idade: Idade do cliente (opcional)
    """
    idade_texto = f" pelos seus {idade} anos" if idade else ""
    
    conteudo = f"""
    <div style="text-align: center; padding: 20px 0;">
        <p style="font-size: 48px; margin: 0;">🎂🎉</p>
    </div>
    
    <p style="font-size: 1.1em;">Prezado(a) <strong>{nome_cliente}</strong>,</p>
    
    <p style="font-size: 1.1em;">
        A equipe do escritório <strong>Lopes & Ribeiro</strong> deseja a você um 
        <span style="color: #3b82f6; font-weight: bold;">Feliz Aniversário</span>{idade_texto}!
    </p>
    
    <div style="background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); padding: 20px; border-radius: 8px; margin: 25px 0; text-align: center;">
        <p style="margin: 0; font-size: 1.2em; color: #92400e;">
            🌟 Que este novo ciclo seja repleto de <strong>saúde</strong>, 
            <strong>realizações</strong> e muitas <strong>conquistas</strong>! 🌟
        </p>
    </div>
    
    <p>É uma satisfação tê-lo(a) como cliente. Continue contando conosco.</p>
    
    <p>Com carinho,<br/>
    <strong>Equipe Lopes & Ribeiro</strong></p>
    """
    return _base_template("🎂 Feliz Aniversário!", conteudo)


def template_atualizacao_processo(
    nome_cliente: str,
    numero_processo: str,
    acao: str,
    atualizacao: str,
    data_atualizacao: str
) -> str:
    """
    Template de notificação de atualização de processo.
    
    Args:
        nome_cliente: Nome do cliente
        numero_processo: Número do processo
        acao: Tipo de ação
        atualizacao: Descrição da atualização/andamento
        data_atualizacao: Data da atualização
    """
    conteudo = f"""
    <p>Prezado(a) <strong>{nome_cliente}</strong>,</p>
    
    <p>Informamos que houve uma <strong>nova movimentação</strong> em seu processo:</p>
    
    <div style="background-color: #ecfdf5; padding: 20px; border-radius: 6px; margin: 20px 0; border-left: 4px solid #10b981;">
        <table style="width: 100%; border-collapse: collapse;">
            <tr>
                <td style="padding: 8px 0; color: #64748b; width: 130px;">📋 Processo:</td>
                <td style="padding: 8px 0; font-weight: bold;">{numero_processo}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">⚖️ Ação:</td>
                <td style="padding: 8px 0;">{acao}</td>
            </tr>
            <tr>
                <td style="padding: 8px 0; color: #64748b;">📅 Data:</td>
                <td style="padding: 8px 0;">{data_atualizacao}</td>
            </tr>
        </table>
        
        <div style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #a7f3d0;">
            <p style="margin: 0; color: #064e3b;"><strong>Movimentação:</strong></p>
            <p style="margin: 10px 0 0 0;">{atualizacao}</p>
        </div>
    </div>
    
    <p>Em caso de dúvidas sobre esta movimentação, entre em contato conosco.</p>
    
    <p>Atenciosamente,<br/>
    <strong>Equipe Lopes & Ribeiro</strong></p>
    """
    return _base_template("📢 Atualização do Seu Processo", conteudo)
