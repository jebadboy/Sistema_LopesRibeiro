"""
Pagina publica para consulta de processos via token.
Permite que clientes acessem o status de seus processos sem login.
"""

import streamlit as st
import token_manager as tm
from datetime import datetime

# Configuracao da pagina
st.set_page_config(
    page_title="Consulta de Processo - Lopes & Ribeiro",
    page_icon="⚖️",
    layout="centered"
)

# Header
st.markdown("""
    <div style='text-align: center; padding: 20px; margin-bottom: 30px;'>
        <h1>⚖️ Lopes & Ribeiro</h1>
        <h3>Advocacia e Consultoria Juridica</h3>
        <p style='color: #666;'>Consulta de Processo</p>
    </div>
""", unsafe_allow_html=True)

# Obter token da URL
query_params = st.query_params
token = query_params.get("token", [None])[0] if "token" in query_params else None

# Se nao houver token na URL, mostrar campo de entrada
if not token:
    st.info("Para consultar seu processo, utilize o link enviado por e-mail ou WhatsApp.")
    
    with st.form("token_form"):
        token_input = st.text_input(
            "Ou cole o token de acesso aqui:",
            placeholder="Cole o token completo..."
        )
        submit = st.form_submit_button("Consultar Processo")
        
        if submit and token_input:
            # Redirecionar para URL com token
            st.query_params["token"] = token_input
            st.rerun()
    
    st.stop()

# Validar token e buscar processo
processo = tm.get_processo_por_token(token)

if not processo:
    st.error("Link invalido ou expirado.")
    st.info("Por favor, entre em contato com o escritorio para obter um novo link de acesso.")
    st.markdown("---")
    st.caption("Lopes & Ribeiro - Advocacia e Consultoria Juridica")
    st.stop()

# --- EXIBIR INFORMACOES DO PROCESSO ---

st.success("Acesso autorizado! Confira abaixo as informacoes do seu processo.")
st.markdown("---")

# Informacoes Basicas
col1, col2 = st.columns(2)

with col1:
    st.markdown("### Dados do Processo")
    
    # Cliente
    if 'cliente' in processo:
        st.markdown(f"**Cliente:** {processo['cliente']['nome']}")
    elif 'cliente_nome' in processo:
        st.markdown(f"**Cliente:** {processo['cliente_nome']}")
    
    # Numero do processo (se existir)
    if 'numero' in processo and processo.get('numero'):
        st.markdown(f"**Numero do Processo:** {processo['numero']}")
    
    # Tipo/Acao
    if 'tipo' in processo:
        st.markdown(f"**Tipo:** {processo['tipo']}")
    elif 'acao' in processo:
        st.markdown(f"**Acao:** {processo['acao']}")

with col2:
    st.markdown("### Status Atual")
    
    status = processo.get('status', 'Nao informado')
    
    # Colorir status
    if status.lower() == 'ativo':
        st.success(f"**Status:** {status}")
    elif status.lower() in ['arquivado', 'encerrado']:
        st.info(f"**Status:** {status}")
    else:
        st.warning(f"**Status:** {status}")
    
    # Responsavel
    if 'responsavel' in processo and processo.get('responsavel'):
        st.markdown(f"**Responsavel:** {processo['responsavel']}")
    
    # Proximo prazo
    if 'proximo_prazo' in processo and processo.get('proximo_prazo'):
        st.markdown(f"**Proximo Prazo:** {processo['proximo_prazo']}")

st.markdown("---")

# Descricao/Objeto do processo
if 'objeto' in processo and processo.get('objeto'):
    st.markdown("### Descricao do Processo")
    st.write(processo['objeto'])
    st.markdown("---")
    
    # --- TIMELINE VISUAL (NOVO) ---
    st.markdown("### 📌 Linha do Tempo do Processo")
    
    # Mapeamento de Fases
    fase_atual = processo.get('fase_processual', 'A Ajuizar')
    
    steps = [
        {"label": "Início", "fases": ["A Ajuizar"], "desc": "Preparação da documentação inicial."},
        {"label": "Análise Liminar", "fases": ["Aguardando Liminar"], "desc": "Juiz analisando pedido de urgência."},
        {"label": "Audiência", "fases": ["Audiência Marcada"], "desc": "Audiência agendada ou realizada."},
        {"label": "Decisão", "fases": ["Sentença", "Em Andamento"], "desc": "Sentença proferida ou processo em curso."},
        {"label": "Finalizado", "fases": ["Arquivado"], "desc": "Processo encerrado."}
    ]
    
    # Determinar índice da fase atual
    current_step_idx = 0
    for i, step in enumerate(steps):
        if fase_atual in step['fases']:
            current_step_idx = i
            break
            
    # CSS para Timeline
    st.markdown("""
<style>
    .timeline-container {
        display: flex;
        justify_content: space-between;
        align_items: center;
        margin: 40px 0;
        position: relative;
    }
    .timeline-line {
        position: absolute;
        top: 15px;
        left: 0;
        width: 100%;
        height: 4px;
        background-color: #e0e0e0;
        z-index: 0;
    }
    .timeline-step {
        position: relative;
        z-index: 1;
        text-align: center;
        width: 20%;
    }
    .dot {
        width: 30px;
        height: 30px;
        border-radius: 50%;
        background-color: #e0e0e0;
        margin: 0 auto 10px;
        display: flex;
        align_items: center;
        justify_content: center;
        color: white;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .step-label {
        font-size: 0.85em;
        color: #666;
    }
    
    /* Estados */
    .completed .dot {
        background-color: #28a745; /* Verde */
    }
    .active .dot {
        background-color: #007bff; /* Azul */
        box-shadow: 0 0 0 5px rgba(0, 123, 255, 0.2);
        transform: scale(1.1);
    }
    .active .step-label {
        color: #007bff;
        font-weight: bold;
    }
    
    /* Tooltip simples */
    .timeline-step:hover .tooltip {
        visibility: visible;
        opacity: 1;
    }
    .tooltip {
        visibility: hidden;
        width: 120px;
        background-color: #333;
        color: #fff;
        text-align: center;
        border-radius: 6px;
        padding: 5px;
        position: absolute;
        z-index: 1;
        bottom: 100%;
        left: 50%;
        margin-left: -60px;
        opacity: 0;
        transition: opacity 0.3s;
        font-size: 0.75em;
    }
    .tooltip::after {
        content: "";
        position: absolute;
        top: 100%;
        left: 50%;
        margin-left: -5px;
        border-width: 5px;
        border-style: solid;
        border-color: #333 transparent transparent transparent;
    }
</style>
    """, unsafe_allow_html=True)
    
    # HTML da Timeline
    html_steps = ""
    for i, step in enumerate(steps):
        status_class = ""
        icon = str(i + 1)
        
        if i < current_step_idx:
            status_class = "completed"
            icon = "✓"
        elif i == current_step_idx:
            status_class = "active"
        
        html_steps += f"""
<div class="timeline-step {status_class}">
    <div class="dot">{icon}</div>
    <div class="step-label">{step['label']}</div>
    <div class="tooltip">{step['desc']}</div>
</div>
"""
        
    st.markdown(f"""
<div class="timeline-container">
    <div class="timeline-line"></div>
    {html_steps}
</div>
    """, unsafe_allow_html=True)

# Timeline de Andamentos
st.markdown("### Movimentacoes Processuais")

if 'andamentos' in processo and len(processo['andamentos']) > 0:
    for andamento in processo['andamentos']:
        # Formatar data
        try:
            if andamento.get('data'):
                data_obj = datetime.fromisoformat(andamento['data'])
                data_formatada = data_obj.strftime("%d/%m/%Y")
            else:
                data_formatada = "Data nao informada"
        except:
            data_formatada = andamento.get('data', 'Data nao informada')
        
        # Exibir andamento
        st.markdown(f"""
            <div style='padding: 15px; margin: 10px 0; 
                 border-left: 4px solid #1f77b4; 
                 background-color: #f8f9fa;
                 border-radius: 4px;'>
                <div style='font-weight: bold; color: #1f77b4; margin-bottom: 5px;'>
                    {data_formatada}
                </div>
                <div style='color: #333;'>
                    {andamento.get('descricao', 'Sem descricao')}
                </div>
                {f"<div style='color: #666; font-size: 0.9em; margin-top: 5px;'>Responsavel: {andamento.get('responsavel')}</div>" if andamento.get('responsavel') else ""}
            </div>
        """, unsafe_allow_html=True)
else:
    st.info("Nenhuma movimentacao registrada ainda.")
    st.caption("As movimentacoes serao atualizadas conforme o andamento do processo.")

st.markdown("---")

# Contato
st.markdown("### Precisa de mais informacoes?")
st.write("Entre em contato com nosso escritorio:")

col_cont1, col_cont2 = st.columns(2)

with col_cont1:
    st.markdown("**Telefone/WhatsApp:**")
    st.markdown("(XX) XXXXX-XXXX")

with col_cont2:
    st.markdown("**E-mail:**")
    st.markdown("contato@lopesribeiro.com.br")

st.markdown("---")

# Footer
st.caption("Este link e confidencial e personalizado para voce. Nao compartilhe com terceiros.")
st.caption("© Lopes & Ribeiro - Todos os direitos reservados")
