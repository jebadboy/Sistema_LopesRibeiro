import streamlit as st
import database as db
import pandas as pd
from datetime import datetime

def render(token):
    """
    Renderiza a tela pública de consulta de processo.
    """
    # Configuração visual simplificada para o cliente
    st.markdown("""
        <style>
            .stAppHeader {display: none;}
            .reportview-container .main .block-container {padding-top: 2rem;}
            .card-processo {
                background-color: #f8f9fa;
                border-left: 5px solid #004a99;
                padding: 20px;
                border-radius: 5px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .status-badge {
                padding: 5px 10px;
                border-radius: 15px;
                font-weight: bold;
                color: white;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown("<div style='text-align: center;'><h2>⚖️ Lopes & Ribeiro</h2><p>Consulta Pública de Processo</p></div>", unsafe_allow_html=True)
    st.markdown("---")

    # Buscar processo pelo token
    try:
        with db.get_connection() as conn:
            query = "SELECT * FROM processos WHERE token_acesso = ?"
            processo = pd.read_sql_query(query, conn, params=(token,))
    except Exception as e:
        st.error("Erro ao conectar ao sistema. Tente novamente mais tarde.")
        return

    if processo.empty:
        st.error("❌ Processo não encontrado ou link inválido.")
        st.info("Verifique se o link está correto ou entre em contato com o escritório.")
        return

    proc = processo.iloc[0]

    # Exibir Detalhes do Processo (Apenas informações públicas/seguras)
    with st.container():
        st.markdown(f"""
            <div class="card-processo">
                <h3>Processo #{proc['id']}</h3>
                <p><strong>Ação:</strong> {proc['acao']}</p>
                <p><strong>Status Atual:</strong> <span style="background-color: #28a745; padding: 3px 8px; border-radius: 4px; color: white;">{proc['status']}</span></p>
                <p><strong>Próximo Prazo/Evento:</strong> {proc['proximo_prazo'] if proc['proximo_prazo'] else 'Não há prazos pendentes'}</p>
            </div>
        """, unsafe_allow_html=True)

    # Buscar e Exibir Histórico de Andamentos (Timeline simplificada)
    st.subheader("📅 Histórico de Andamentos")
    
    historico = db.get_historico(proc['id'])
    
    if not historico.empty:
        for index, row in historico.iterrows():
            data_fmt = datetime.strptime(row['data'], "%Y-%m-%d").strftime("%d/%m/%Y")
            with st.expander(f"{data_fmt} - {row['descricao'][:50]}...", expanded=(index==0)):
                st.write(f"**Data:** {data_fmt}")
                st.write(f"**Descrição:** {row['descricao']}")
                st.caption(f"Responsável: {row['responsavel']}")
    else:
        st.info("Nenhum andamento registrado até o momento.")

    st.markdown("---")
    st.caption("Este é um link seguro e exclusivo para consulta. Não compartilhe com terceiros não autorizados.")
    
    # Botão de contato (WhatsApp Link)
    st.markdown("""
        <div style="text-align: center; margin-top: 20px;">
            <a href="https://wa.me/5511999999999" target="_blank" style="background-color: #25D366; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; font-weight: bold;">
                💬 Falar com Advogado no WhatsApp
            </a>
        </div>
    """, unsafe_allow_html=True)
