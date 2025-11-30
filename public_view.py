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
    if 'numero_processo' in processo and processo.get('numero_processo'):
        st.markdown(f"**Numero do Processo:** {processo['numero_processo']}")
    
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
