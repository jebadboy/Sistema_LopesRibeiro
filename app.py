import streamlit as st
from datetime import datetime
import database as db
import utils as ut
import logging
import os
import pandas as pd
from streamlit_calendar import calendar

st.set_page_config(page_title="Lopes & Ribeiro System", page_icon="⚖️", layout="wide")

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_lopes_ribeiro.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONSTANTES CONFIGURÁVEIS ---
RESPONSAVEIS = ["Eduardo", "Sheila"]
STATUS_PROCESSO = ["Ativo", "Arquivado", "Suspenso", "Finalizado"]

db.init_db()

# Backup automático diário
if 'ultimo_backup' not in st.session_state:
    st.session_state.ultimo_backup = None

if st.session_state.ultimo_backup is None or \
   (datetime.now() - st.session_state.ultimo_backup).days >= 1:
    try:
        resultado = db.backup_database()
        st.session_state.ultimo_backup = datetime.now()
        logger.info(f"Backup automático criado: {resultado}")
    except Exception as e:
        logger.error(f"Erro ao criar backup automático: {e}")
                        if not modelos.empty:
                            mod_sel = st.selectbox("Selecione um Modelo:", modelos['nome_modelo'].tolist())
                            if st.button("Gerar Texto da Proposta"):
                                id_mod = modelos[modelos['nome_modelo'] == mod_sel].iloc[0]['id']
                                texto_prop = db.gerar_proposta_texto(id_mod, dd)
                                st.text_area("Texto Gerado (Copie e Cole)", value=texto_prop, height=300)
                        else:
                            st.caption("Nenhum modelo cadastrado. Vá na aba 'Modelos de Proposta'.")

                        st.divider()
                        cb1, cb2 = st.columns(2)
                        if cb1.button("💾 Salvar Dados da Proposta"):
                            try:
                                db.sql_run("UPDATE clientes SET proposta_valor=?, proposta_entrada=?, proposta_parcelas=?, proposta_pagamento=?, proposta_objeto=? WHERE id=?", 
                                           (vp, ve, np, pg, ob, int(dd['id'])))
                                logger.info(f"Proposta atualizada para cliente {dd['nome']} (ID: {dd['id']})")
                                st.success("Salvo!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Erro ao salvar proposta: {e}")
                                logger.error(f"Erro ao salvar proposta do cliente ID {dd['id']}: {e}")
                        with cb2:
                            doc = ut.criar_doc("Proposta", {'nome':dd['nome'], 'proposta_valor':vp, 'proposta_entrada':ve, 'proposta_parcelas':np, 'proposta_objeto':ob, 'proposta_pagamento':pg})
                            st.download_button("📄 Baixar DOC Simples", doc, f"Prop_{sel}.docx", type="primary")

                    # MODO DOCS FINAIS (SÓ SE ATIVO)
                    if dd['status_cliente'] == 'ATIVO':
                        st.markdown("### 🖨️ Documentos Finais")
                        d1, d2, d3 = st.columns(3)
                        with d1: st.download_button("Procuração", ut.criar_doc("Procuracao", dd), "proc.docx")
                        with d2: st.download_button("Hipossuf.", ut.criar_doc("Hipossuficiencia", dd), "hipo.docx")
                        with d3: st.download_button("Contrato", ut.criar_doc("Contrato", dd), "cont.docx")

                    # EXCLUIR
                    if st.button("🗑️ Excluir Cliente"):
                        try:
                            db.sql_run("DELETE FROM clientes WHERE id=?", (int(dd['id']),))
                            logger.info(f"Cliente {dd['nome']} excluído (ID: {dd['id']})")
                            st.success("Cliente excluído!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Erro ao excluir: {e}")

            st.dataframe(df[['nome','CPF','Celular','status_cliente']], use_container_width=True)
        else: st.info("Nenhum cliente.")

    # --- ABA 3: KANBAN DE VENDAS ---
    with t3:
        st.markdown("### 📊 Funil de Vendas")
        
        # Colunas do Kanban
        k1, k2, k3 = st.columns(3)
        
        # Buscar todos os clientes
        df_k = db.sql_get("clientes")
        
        # Coluna 1: Em Negociação
        with k1:
            st.info("🟡 Em Negociação")
            if not df_k.empty:
                neg = df_k[df_k['status_cliente'] == 'EM NEGOCIAÇÃO']
                for _, row in neg.iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")
                        st.caption(f"Valor: R$ {ut.safe_float(row['proposta_valor']):,.2f}")
                        if st.button("➡️ Fechar", key=f"win_{row['id']}"):
                            db.sql_run("UPDATE clientes SET status_cliente='ATIVO' WHERE id=?", (row['id'],))
                            st.rerun()
                            
        # Coluna 2: Ativos (Fechados Recentemente)
        with k2:
            st.success("🟢 Fechado / Ativo")
            if not df_k.empty:
                # Mostrar apenas os 10 últimos ativos para não poluir
                ativos = df_k[df_k['status_cliente'] == 'ATIVO'].sort_values(by='id', ascending=False).head(10)
                for _, row in ativos.iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")
                        st.caption("Cliente Ativo")

        # Coluna 3: Perdidos / Inativos
        with k3:
            st.error("🔴 Perdido / Inativo")
            if not df_k.empty:
                inativos = df_k[df_k['status_cliente'] == 'INATIVO'].head(10)
                for _, row in inativos.iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")
                        if st.button("♻️ Reativar", key=f"react_{row['id']}"):
                            db.sql_run("UPDATE clientes SET status_cliente='EM NEGOCIAÇÃO' WHERE id=?", (row['id'],))
                            st.rerun()

    # --- ABA 4: MODELOS DE PROPOSTA ---
    with t4:
        st.markdown("### 📝 Gerenciar Modelos")
        
        # Novo Modelo
        with st.expander("➕ Criar Novo Modelo"):
            with st.form("form_modelo"):
                mnome = st.text_input("Nome do Modelo (ex: Honorários Previdenciários)")
                mdesc = st.text_input("Área / Descrição")
                mvalor = st.number_input("Valor Sugerido (R$)", min_value=0.0)
                mtexto = st.text_area("Texto Padrão (Use {nome}, {cpf}, {valor} como variáveis)", height=200)
                
                if st.form_submit_button("Salvar Modelo"):
                    if mnome and mtexto:
                        db.salvar_modelo_proposta(mnome, mtexto, mdesc, mvalor)
                        st.success("Modelo Salvo!")
                        st.rerun()
                    else:
                        st.error("Nome e Texto são obrigatórios.")
        
        # Listar Modelos
        mods = db.get_modelos_proposta()
        if not mods.empty:
            st.dataframe(mods[['nome_modelo', 'area_atuacao', 'valor_sugerido']], use_container_width=True)
        else:
            st.info("Nenhum modelo cadastrado.")

# ==========================================
# 2. FINANCEIRO
# ==========================================
elif menu == "Financeiro":
    st.title("💰 Financeiro")
    t1, t2, t3, t4 = st.tabs(["💸 Lançar", "📜 Extrato", "📊 Relatórios", "🔢 Parcelamento"])
    
    with t1:
        st.markdown("### Novo Lançamento")
        with st.form("fin_form"):
            c1,c2 = st.columns(2)
            tipo = c1.selectbox("Tipo", ["Entrada", "Saída"])
            cat = c2.text_input("Categoria (ex: Honorários, Aluguel)")
            desc = st.text_input("Descrição")
            val = st.number_input("Valor (R$)", min_value=0.01)
            
            c3,c4 = st.columns(2)
            dt = c3.date_input("Data", value=datetime.now())
            resp = c4.selectbox("Responsável", RESPONSAVEIS)
            
            # --- PARCERIA / REPASSE ---
            with st.expander("🤝 Parceria / Repasse (Opcional)"):
                tem_parceiro = st.checkbox("Tem Parceiro?")
                if tem_parceiro:
                    parceiro_nome = st.text_input("Nome do Parceiro")
                    perc_parceria = st.number_input("Percentual de Repasse (%)", min_value=0.0, max_value=100.0, value=30.0)
                else:
                    parceiro_nome = None
                    perc_parceria = 0.0

            if st.form_submit_button("Lançar"):
                try:
                    db.sql_run("INSERT INTO financeiro (data, tipo, categoria, descricao, valor, responsavel, status_pagamento, vencimento, percentual_parceria) VALUES (?,?,?,?,?,?,?,?,?)",
                               (dt, tipo, cat, desc, val, resp, 'Pendente', dt, perc_parceria if tem_parceiro else 0))
                    st.success("Lançamento realizado!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro: {e}")

    with t2:
        st.markdown("### Extrato / Baixa")
        c_f1, c_f2 = st.columns(2)
        dt_ini = c_f1.date_input("De", value=datetime(datetime.now().year, datetime.now().month, 1))
        dt_fim = c_f2.date_input("Até", value=datetime.now())
        
        df = db.sql_get("financeiro")
        if not df.empty:
            df['data_dt'] = pd.to_datetime(df['data'])
            df = df[(df['data_dt'].dt.date >= dt_ini) & (df['data_dt'].dt.date <= dt_fim)]
            st.dataframe(df.sort_values(by='data', ascending=False), use_container_width=True)
            
            lancs = df[df['status_pagamento'] == 'Pendente']
            if not lancs.empty:
                bx = st.selectbox("Dar Baixa (ID - Desc):", lancs['id'].astype(str) + " - " + lancs['descricao'])
                if st.button("Confirmar Pagamento"):
                    lid = int(bx.split(" - ")[0])
                    db.sql_run("UPDATE financeiro SET status_pagamento='Pago' WHERE id=?", (lid,))
                    if db.processar_repasse(lid):
                        st.success("Pago! Repasse de parceiro gerado automaticamente.")
                    else:
                        st.success("Pago!")
                    st.rerun()
        else:
            st.info("Sem lançamentos no período.")

    with t3:
        st.markdown("### Relatórios")
        if st.button("Gerar Relatório Excel"):
            df_rel = db.sql_get("financeiro")
            if not df_rel.empty:
                path = db.exportar_para_excel(df_rel, f"financeiro_{datetime.now().strftime('%Y%m%d')}")
                with open(path, "rb") as f:
                    st.download_button("Baixar Excel", f, file_name=os.path.basename(path))
    
    with t4:
        st.markdown("### Gerador de Carnê / Parcelamento")
        with st.form("form_carne"):
            cp_desc = st.text_input("Descrição (ex: Honorários Silva)")
            cp_val = st.number_input("Valor Total", min_value=0.01)
            cp_qtd = st.number_input("Qtd Parcelas", min_value=2, step=1)
            cp_dt = st.date_input("1ª Vencimento")
            if st.form_submit_button("Gerar Parcelas"):
                st.info("Funcionalidade em desenvolvimento.")

# ==========================================
# 3. PROCESSOS
# ==========================================
elif menu == "Processos":
    st.title("⚖️ Gestão de Processos")
    t1, t2 = st.tabs(["📂 Lista de Processos", "➕ Novo Processo"])
    
    with t1:
        df_proc = db.sql_get("processos")
        if not df_proc.empty:
            filtro = st.text_input("🔍 Buscar Processo (Nome, Ação)")
            if filtro:
                df_proc = df_proc[df_proc['cliente_nome'].str.contains(filtro, case=False) | df_proc['acao'].str.contains(filtro, case=False)]
            
            st.dataframe(df_proc, use_container_width=True)
            
            # Seleção para Detalhes
            proc_opts = df_proc['id'].astype(str) + " - " + df_proc['cliente_nome'] + " (" + df_proc['acao'] + ")"
            sel_proc = st.selectbox("Ver Detalhes:", ["Selecione..."] + proc_opts.tolist())
            
            if sel_proc != "Selecione...":
                id_proc = int(sel_proc.split(" - ")[0])
                proc_dados = df_proc[df_proc['id'] == id_proc].iloc[0]
                
                st.divider()
                st.subheader(f"Processo #{id_proc}: {proc_dados['cliente_nome']}")
                
                tp1, tp2, tp3 = st.tabs(["📅 Timeline (Andamentos)", "📂 Documentos", "💰 Financeiro Vinculado"])
                
                with tp1:
                    st.markdown("#### Histórico de Andamentos")
                    hist = db.get_historico(id_proc)
                    if not hist.empty:
                        for _, h in hist.iterrows():
                            st.text(f"{h['data']} - {h['descricao']} ({h['responsavel']})")
                    else:
                        st.info("Nenhum andamento registrado.")
                    
                    with st.form(f"add_andamento_{id_proc}"):
                        st.markdown("##### Novo Andamento")
                        desc_and = st.text_input("Descrição")
                        data_and = st.date_input("Data", value=datetime.now())
                        resp_and = st.selectbox("Responsável", RESPONSAVEIS)
                        if st.form_submit_button("Adicionar Andamento"):
                            db.crud_insert("andamentos", {
                                "id_processo": id_proc,
                                "data": data_and.strftime("%Y-%m-%d"),
                                "descricao": desc_and,
                                "responsavel": resp_and
                            })
                            st.success("Andamento adicionado!")
                            st.rerun()

                with tp2:
                    st.markdown("#### Documentos do Processo")
                    docs = db.get_documentos_processo(id_proc)
                    if not docs.empty:
                        for _, d in docs.iterrows():
                            st.markdown(f"[{d['tipo_documento']}] **{d['nome_documento']}** - [Abrir]({d['link_drive']})")
                    
                    with st.form(f"add_doc_{id_proc}"):
                        st.markdown("##### Vincular Documento")
                        tipo_doc = st.selectbox("Tipo", ['peticao_inicial', 'procuracao', 'sentenca', 'acordao', 'outro'])
                        nome_doc = st.text_input("Nome do Arquivo")
                        link_doc = st.text_input("Link (Google Drive/Sharepoint)")
                        if st.form_submit_button("Salvar Documento"):
                            if nome_doc and link_doc:
                                db.crud_insert("documentos_processo", {
                                    "id_processo": id_proc,
                                    "tipo_documento": tipo_doc,
                                    "nome_documento": nome_doc,
                                    "link_drive": link_doc
                                })
                                st.success("Documento vinculado!")
                                st.rerun()
                            else:
                                st.error("Preencha nome e link.")

                with tp3:
                    st.markdown("#### Financeiro do Processo")
                    vincs = db.get_vinculos_financeiros(id_proc)
                    if not vincs.empty:
                        st.dataframe(vincs)
                    else:
                        st.info("Nenhum lançamento financeiro vinculado a este processo.")

        else:
            st.info("Nenhum processo cadastrado.")

    with t2:
        st.markdown("### Cadastro de Processo")
        with st.form("novo_proc_form"):
            p_cliente = st.text_input("Nome do Cliente")
            p_acao = st.text_input("Ação / Causa")
            p_prazo = st.date_input("Próximo Prazo")
            p_resp = st.selectbox("Responsável", RESPONSAVEIS)
            
            if st.form_submit_button("Cadastrar Processo"):
                if p_cliente and p_acao:
                    db.crud_insert("processos", {
                        "cliente_nome": p_cliente,
                        "acao": p_acao,
                        "proximo_prazo": p_prazo.strftime("%Y-%m-%d"),
                        "responsavel": p_resp,
                        "status": "Ativo"
                    })
                    st.success("Processo criado!")
                    st.rerun()
                else:
                    st.error("Preencha os campos obrigatórios.")

# ==========================================
# 4. AGENDA
# ==========================================
elif menu == "Agenda":
    st.title("📅 Agenda & Tarefas")
    
    # Integração simples com Calendar
    events = []
    # Buscar eventos do banco
    try:
        df_agenda = db.get_agenda_eventos()
        if not df_agenda.empty:
            for _, row in df_agenda.iterrows():
                events.append({
                    "title": f"{row['tipo'].upper()}: {row['titulo']}",
                    "start": row['data_evento'],
                    "backgroundColor": row['cor'] if row['cor'] else "#3788d8"
                })
    except Exception as e:
        st.error(f"Erro ao carregar agenda: {e}")

    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "initialView": "dayGridMonth",
    }
    
    calendar(events=events, options=calendar_options)
    
    with st.expander("➕ Adicionar Evento / Prazo"):
        with st.form("agenda_form"):
            a_titulo = st.text_input("Título")
            a_tipo = st.selectbox("Tipo", ["prazo", "audiencia", "tarefa"])
            a_data = st.date_input("Data")
            a_hora = st.time_input("Hora", value=datetime.now().time())
            a_resp = st.selectbox("Responsável", RESPONSAVEIS)
            
            if st.form_submit_button("Salvar na Agenda"):
                dt_evento = f"{a_data} {a_hora}"
                db.crud_insert("agenda", {
                    "titulo": a_titulo,
                    "tipo": a_tipo,
                    "data_evento": dt_evento,
                    "responsavel": a_resp,
                    "status": "pendente"
                })
                st.success("Evento agendado!")
                st.rerun()

# ==========================================
# 5. IA JURÍDICA
# ==========================================
elif menu == "IA Jurídica":
    st.title("🤖 IA Jurídica (Beta)")
    
    if not ut.API_KEY_GEMINI:
        st.warning("⚠️ Chave de API do Google Gemini não configurada. Verifique o arquivo .env ou secrets.")
    else:
        t1, t2 = st.tabs(["💬 Chat Assistente", "🛠️ Ferramentas Rápidas"])
        
        # --- CHAT ---
        with t1:
            st.caption("Converse com o assistente sobre processos, teses ou dúvidas jurídicas.")
            
            if "messages" not in st.session_state:
                st.session_state.messages = []

            for message in st.session_state.messages:
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])

            if prompt := st.chat_input("Digite sua dúvida jurídica..."):
                st.session_state.messages.append({"role": "user", "content": prompt})
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Pensando..."):
                        response = ut.consultar_ia(prompt)
                        st.markdown(response)
                st.session_state.messages.append({"role": "assistant", "content": response})

        # --- FERRAMENTAS ---
        with t2:
            st.markdown("### ⚡ Geradores Automáticos")
            
            ferramenta = st.selectbox("Escolha uma ferramenta:", 
                                      ["Resumir Texto Jurídico", "Gerar E-mail de Cobrança", "Revisar Contrato (Simples)"])
            
            if ferramenta == "Resumir Texto Jurídico":
                txt_input = st.text_area("Cole o texto aqui:")
                if st.button("Resumir"):
                    if txt_input:
                        with st.spinner("Resumindo..."):
                            res = ut.consultar_ia(f"Resuma este texto jurídico em tópicos simples para um cliente leigo entender: {txt_input}")
                            st.markdown(res)
                    else: st.warning("Cole um texto.")
            
            elif ferramenta == "Gerar E-mail de Cobrança":
                c_nome = st.text_input("Nome do Cliente")
                c_valor = st.text_input("Valor em Aberto")
                c_servico = st.text_input("Serviço Prestado")
                if st.button("Gerar E-mail"):
                    prompt_mail = f"Escreva um e-mail formal e educado de cobrança para o cliente {c_nome}, referente ao serviço {c_servico} no valor de {c_valor}. O tom deve ser amigável mas firme."
                    with st.spinner("Escrevendo..."):
                        st.text_area("E-mail Sugerido:", value=ut.consultar_ia(prompt_mail), height=300)

            elif ferramenta == "Revisar Contrato (Simples)":
                txt_contrato = st.text_area("Cole as cláusulas do contrato:")
                if st.button("Revisar"):
                    if txt_contrato:
                        with st.spinner("Analisando..."):
                            res = ut.consultar_ia(f"Analise este contrato e aponte possíveis cláusulas abusivas ou riscos para a parte contratante: {txt_contrato}")
                            st.markdown(res)

# ==========================================
# 6. PAINEL GERAL
# ==========================================
elif menu == "Painel Geral":
    st.title("📊 Painel de Controle")
    
    # KPIs
    try:
        s, r, nc, np = db.kpis()
    except:
        s, r, nc, np = 0, 0, 0, 0
        
    c1,c2,c3,c4=st.columns(4)
    c1.metric("Caixa (Saldo)", ut.formatar_moeda(s))
    c2.metric("A Receber", ut.formatar_moeda(r))
    c3.metric("Clientes Ativos", nc)
    c4.metric("Processos Ativos", np)
    
    st.divider()
    
    # --- GRÁFICOS ---
    g1, g2 = st.columns(2)
    
    with g1:
        st.subheader("💰 Faturamento (Entradas x Saídas)")
        df_fin = db.sql_get("financeiro")
        if not df_fin.empty:
            # Agrupar por Mês e Tipo
            df_fin['data'] = pd.to_datetime(df_fin['data'])
            df_fin['mes_ano'] = df_fin['data'].dt.strftime('%Y-%m')
            chart_data = df_fin.groupby(['mes_ano', 'tipo'])['valor'].sum().unstack().fillna(0)
            st.bar_chart(chart_data)
        else:
            st.info("Sem dados financeiros.")
            
    with g2:
        st.subheader("👥 Clientes por Status")
        df_cli = db.sql_get("clientes")
        if not df_cli.empty:
            status_counts = df_cli['status_cliente'].value_counts()
            st.bar_chart(status_counts) # Streamlit nativo não tem pizza fácil, barra é melhor
        else:
            st.info("Sem dados de clientes.")

    st.divider()
    
    # Backup manual seguro
    st.markdown("### 💾 Gestão de Backups")
    col_bkp1, col_bkp2 = st.columns(2)
    
    with col_bkp1:
        if st.button("💾 Criar Backup Agora", type="primary"):
            try:
                resultado = db.backup_database()
                st.success(resultado)
                logger.info("Backup manual criado pelo usuário")
            except Exception as e:
                st.error(f"Erro ao criar backup: {e}")
    
    with col_bkp2:
        if os.path.exists('backups'):
            backups = sorted([f for f in os.listdir('backups') if f.endswith('.db')], reverse=True)
            if backups:
                st.caption(f"{len(backups)} backup(s) disponível(is)")
                # Download do último
                with open(f'backups/{backups[0]}', 'rb') as fp:
                    st.download_button(f"📥 Baixar Último ({backups[0]})", fp, backups[0])