import streamlit as st
import database as db
import utils as ut

def render():
    st.markdown("<h1 style='color: var(--text-main);'>📊 Painel de Controle</h1>", unsafe_allow_html=True)
    
    # Calcular KPIs
    saldo, receber, num_clientes, num_processos = db.kpis() if hasattr(db, 'kpis') else (0, 0, 0, 0)
    
    # Recalcular KPIs manualmente se a função do DB não estiver 100% (garantia)
    # A função db.kpis() original já faz isso, mas vamos garantir a exibição correta
    
    # Layout de Cards
    c1, c2, c3, c4 = st.columns(4)
    
    with c1:
        render_kpi_card("Caixa Atual", ut.formatar_moeda(saldo), "status-success" if saldo >= 0 else "status-danger")
    with c2:
        render_kpi_card("A Receber", ut.formatar_moeda(receber), "status-warning")
    with c3:
        render_kpi_card("Clientes Ativos", str(num_clientes), "status-neutral")
    with c4:
        render_kpi_card("Processos", str(num_processos), "status-neutral")
        
    st.divider()
    
    # Área de Manutenção
    st.markdown("### 🛠️ Manutenção do Sistema")
    
    col_bkp, col_info = st.columns([1, 2])
    
    with col_bkp:
        with open("dados_escritorio.db", "rb") as fp:
            st.download_button(
                "💾 Fazer Backup Completo (DB)", 
                fp, 
                "backup_sistema.db", 
                type="primary",
                use_container_width=True
            )
            
    with col_info:
        st.info("O backup salva todos os clientes, processos e lançamentos financeiros. Faça isso semanalmente.")

def render_kpi_card(label, value, status_class=""):
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-label">{label}</div>
        <div class="metric-value {status_class}">{value}</div>
    </div>
    """, unsafe_allow_html=True)
