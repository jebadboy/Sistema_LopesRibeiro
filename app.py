import streamlit as st
from datetime import datetime
import database as db
import utils as ut
import logging
import os
import pandas as pd
from streamlit_calendar import calendar

st.set_page_config(page_title="Lopes & Ribeiro System", page_icon="⚖️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Inter:wght@400;600&display=swap');
    .stApp { background: linear-gradient(135deg, #FAFAF8 0%, #F5F5F0 100%); color: #2C2C2C; font-family: 'Inter', sans-serif; }
    section[data-testid="stSidebar"] { background-color: #FFFFFF; border-right: 2px solid #D4AF37; box-shadow: 2px 0 10px rgba(0,0,0,0.05); }
    h1 { color: #B8860B !important; font-family: 'Playfair Display', serif; border-bottom: 3px solid #D4AF37; padding-bottom: 0.5rem; }
    h2, h3 { color: #C19A2B !important; font-family: 'Playfair Display', serif; }
    .stTextInput > div > div > input, .stNumberInput > div > div > input, .stDateInput > div > div > input, .stTextArea > div > div > textarea {
        background-color: #FFFFFF; border: 1.5px solid #E0E0E0; border-radius: 6px; transition: all 0.3s ease;
    }
    .stTextInput > div > div > input:focus, .stNumberInput > div > div > input:focus, .stDateInput > div > div > input:focus, .stTextArea > div > div > textarea:focus {
        border-color: #D4AF37 !important; box-shadow: 0 0 0 3px rgba(212, 175, 55, 0.1);
    }
    .stTextInput label, .stNumberInput label, .stSelectbox label, .stDateInput label, .stTextArea label { color: #8B7355 !important; font-weight: 600 !important; }
    .stButton > button {
        background: linear-gradient(135deg, #D4AF37 0%, #C19A2B 100%); color: #FFFFFF; font-weight: 700; border-radius: 6px;
        box-shadow: 0 4px 6px rgba(212, 175, 55, 0.2); text-transform: uppercase;
    }
    .stButton > button:hover { background: linear-gradient(135deg, #C19A2B 0%, #B8860B 100%); transform: translateY(-2px); }
    div[data-testid="stMetric"] { background-color: #FFFFFF; padding: 1.2rem; border-radius: 10px; border-left: 5px solid #D4AF37; box-shadow: 0 3px 10px rgba(0, 0, 0, 0.06); }
    .stTabs [data-baseweb="tab"] { background-color: #F5F5F5; border-radius: 8px 8px 0 0; font-weight: 500; }
    .stTabs [aria-selected="true"] { background: linear-gradient(135deg, #D4AF37 0%, #C19A2B 100%); color: #FFFFFF !important; font-weight: 700; }
    ::-webkit-scrollbar { width: 10px; }
    ::-webkit-scrollbar-track { background: #F5F5F5; }
    ::-webkit-scrollbar-thumb { background: linear-gradient(135deg, #D4AF37 0%, #C19A2B 100%); border-radius: 10px; }
</style>
""", unsafe_allow_html=True)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistema_lopes_ribeiro.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- CONSTANTES CONFIGURÁVEIS ---
RESPONSAVEIS = ["Eduardo", "Sheila"]
STATUS_PROCESSO = ["Ativo", "Arquivado", "Suspenso", "Finalizado"]

# Inicializar banco de dados
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

# --- SIDEBAR MENU ---
with st.sidebar:
    st.image("https://via.placeholder.com/200x80/1E3A8A/FFFFFF?text=Lopes+%26+Ribeiro", use_container_width=True)
    st.markdown("---")
    menu = st.radio("📋 Menu Principal", 
                    ["Clientes", "Financeiro", "Processos", "Agenda", "IA Jurídica", "Painel Geral"])

# ==========================================
# 1. CLIENTES
# ==========================================
if menu == "Clientes":
    st.title("👥 Gestão de Clientes")
    t1, t2, t3, t4 = st.tabs(["✏️ Cadastro", "📋 Lista", "📊 Kanban de Vendas", "📝 Modelos de Proposta"])
    
    # --- ABA 1: CADASTRO ---
    with t1:
        st.markdown("### 📝 Novo Cliente / Editar")
        
        # Seletor para edição
        df_edit = db.sql_get("clientes")
        if not df_edit.empty:
            edit_opts = ["Novo Cliente"] + (df_edit['id'].astype(str) + " - " + df_edit['nome']).tolist()
            sel_edit = st.selectbox("Selecione para Editar ou Crie Novo:", edit_opts)
        else:
            sel_edit = "Novo Cliente"
        
        # Controle de mudança de seleção
        if 'last_edit_selection' not in st.session_state:
            st.session_state.last_edit_selection = "Novo Cliente"
        
        if st.session_state.last_edit_selection != sel_edit:
            st.session_state.last_edit_selection = sel_edit
            st.rerun()
        
        # Valores iniciais
        if sel_edit != "Novo Cliente":
            id_edit = int(sel_edit.split(" - ")[0])
            dados_edit = df_edit[df_edit['id'] == id_edit].iloc[0]
        else:
            dados_edit = None
        
        # Formulário
        with st.form("form_cliente", clear_on_submit=(sel_edit == "Novo Cliente")):
            st.markdown("#### Dados Pessoais")
            c1, c2 = st.columns(2)
            nome = c1.text_input("Nome Completo*", value=dados_edit['nome'] if dados_edit is not None else "")
            cpf = c2.text_input("CPF/CNPJ*", value=dados_edit['cpf_cnpj'] if dados_edit is not None else "")
            
            c3, c4 = st.columns(2)
            email = c3.text_input("E-mail", value=dados_edit['email'] if dados_edit is not None else "")
            cel = c4.text_input("Celular*", value=dados_edit['telefone'] if dados_edit is not None else "")
            
            c5, c6 = st.columns(2)
            tel_fixo = c5.text_input("Telefone Fixo", value=dados_edit['telefone_fixo'] if dados_edit is not None else "")
            profissao = c6.text_input("Profissão", value=dados_edit['profissao'] if dados_edit is not None else "")
            
            est_civil = st.selectbox("Estado Civil", 
                                     ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"],
                                     index=["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"].index(dados_edit['estado_civil']) if dados_edit is not None and dados_edit['estado_civil'] in ["Solteiro(a)", "Casado(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"] else 0)
            
            st.markdown("#### Endereço")
            cep_input = st.text_input("CEP", value=dados_edit['cep'] if dados_edit is not None else "")
            
            # Buscar CEP
            end_auto, bairro_auto, cidade_auto, uf_auto = "", "", "", ""
            if cep_input and len(ut.limpar_numeros(cep_input)) == 8:
                dados_cep = ut.buscar_cep(cep_input)
                if dados_cep and not dados_cep.get('erro'):
                    end_auto = dados_cep.get('logradouro', '')
                    bairro_auto = dados_cep.get('bairro', '')
                    cidade_auto = dados_cep.get('localidade', '')
                    uf_auto = dados_cep.get('uf', '')
                else:
                    st.toast("⚠️ CEP não encontrado ou inválido", icon="⚠️")
            
            endereco = st.text_input("Endereço", value=end_auto if sel_edit == "Novo Cliente" else (dados_edit['endereco'] if dados_edit is not None else ""))
            c7, c8 = st.columns(2)
            numero = c7.text_input("Número", value=dados_edit['numero_casa'] if dados_edit is not None else "")
            complemento = c8.text_input("Complemento", value=dados_edit['complemento'] if dados_edit is not None else "")
            
            c9, c10, c11 = st.columns(3)
            bairro = c9.text_input("Bairro", value=bairro_auto if sel_edit == "Novo Cliente" else (dados_edit['bairro'] if dados_edit is not None else ""))
            cidade = c10.text_input("Cidade", value=cidade_auto if sel_edit == "Novo Cliente" else (dados_edit['cidade'] if dados_edit is not None else ""))
            uf = c11.text_input("UF", value=uf_auto if sel_edit == "Novo Cliente" else (dados_edit['estado'] if dados_edit is not None else ""), max_chars=2)
            
            st.markdown("#### Informações Adicionais")
            obs = st.text_area("Observações", value=dados_edit['obs'] if dados_edit is not None else "")
            
            c12, c13 = st.columns(2)
            status = c12.selectbox("Status do Cliente", 
                                   ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"],
                                   index=["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"].index(dados_edit['status_cliente']) if dados_edit is not None and dados_edit['status_cliente'] in ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"] else 0)
            link_drive = c13.text_input("Link Google Drive/Pasta", value=dados_edit['link_drive'] if dados_edit is not None else "")
            
            submit = st.form_submit_button("💾 Salvar Cliente", type="primary")
            
            if submit:
                erros = []
                if not nome: erros.append("Nome é obrigatório")
                if not cpf: erros.append("CPF/CNPJ é obrigatório")
                elif not ut.validar_cpf_matematico(cpf): erros.append("CPF inválido")
                if not cel: erros.append("Celular é obrigatório")
                elif not ut.validar_telefone(cel): erros.append("Celular inválido")
                
                if erros:
                    for erro in erros: st.error(f"❌ {erro}")
                else:
                    try:
                        dados_salvar = {
                            "nome": nome, "cpf_cnpj": ut.limpar_numeros(cpf), "email": email,
                            "telefone": ut.limpar_numeros(cel), "telefone_fixo": ut.limpar_numeros(tel_fixo),
                            "profissao": profissao, "estado_civil": est_civil,
                            "cep": ut.limpar_numeros(cep_input), "endereco": endereco,
                            "numero_casa": numero, "complemento": complemento,
                            "bairro": bairro, "cidade": cidade, "estado": uf.upper(),
                            "obs": obs, "status_cliente": status, "link_drive": link_drive
                        }
                        
                        if sel_edit == "Novo Cliente":
                            if db.cpf_existe(ut.limpar_numeros(cpf)):
                                st.error("❌ CPF já cadastrado!")
                            else:
                                dados_salvar["data_cadastro"] = datetime.now().strftime("%Y-%m-%d")
                                db.crud_insert("clientes", dados_salvar, contexto=f"Cadastro: {nome}")
                                st.success("✅ Cliente cadastrado!")
                                st.rerun()
                        else:
                            cpf_limpo = ut.limpar_numeros(cpf)
                            cpf_atual = dados_edit['cpf_cnpj']
                            if cpf_limpo != cpf_atual and db.cpf_existe(cpf_limpo):
                                st.error("❌ CPF já pertence a outro cliente!")
                            else:
                                db.crud_update("clientes", dados_salvar, "id = ?", (id_edit,), contexto=f"Update: {nome}")
                                st.success("✅ Cliente atualizado!")
                                st.rerun()
                    except Exception as e:
                        st.error(f"❌ Erro ao salvar: {e}")

    # --- ABA 2: LISTA E PROPOSTAS ---
    with t2:
        st.markdown("### 📋 Lista de Clientes")
        df = db.sql_get("clientes", "nome")
        
        if not df.empty:
            col_f1, col_f2 = st.columns(2)
            filtro_status = col_f1.multiselect("Filtrar Status:", ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"], default=["EM NEGOCIAÇÃO", "ATIVO"])
            busca = col_f2.text_input("🔍 Buscar:")
            
            df_filtrado = df[df['status_cliente'].isin(filtro_status)]
            if busca:
                df_filtrado = df_filtrado[df_filtrado['nome'].str.contains(busca, case=False, na=False) | df_filtrado['cpf_cnpj'].str.contains(busca, case=False, na=False)]
            
            if not df_filtrado.empty:
                opts = df_filtrado['id'].astype(str) + " - " + df_filtrado['nome']
                sel = st.selectbox("Selecione Cliente:", ["Selecione..."] + opts.tolist())
                
                if sel != "Selecione...":
                    id_cli = int(sel.split(" - ")[0])
                    dd = df[df['id'] == id_cli].iloc[0].to_dict()
                    
                    st.divider()
                    st.subheader(f"📋 {dd['nome']}")
                    
                    c_b1, c_b2, c_b3 = st.columns(3)
                    c_b1.metric("Status", dd['status_cliente'])
                    c_b2.metric("Inadimplência", db.ver_inadimplencia(dd['nome']))
                    if dd['telefone']: c_b3.markdown(f"[📱 WhatsApp]({ut.formatar_link_zap(dd['telefone'])})")
                    
                    tabs_det = st.tabs(["📄 Dados", "💼 Proposta", "📄 Documentos Finais"])
                    
                    with tabs_det[0]:
                        st.text(f"CPF: {ut.formatar_cpf(dd['cpf_cnpj'])}")
                        st.text(f"Endereço: {dd['endereco']}, {dd['numero_casa']} - {dd['bairro']}, {dd['cidade']}/{dd['estado']}")
                        st.text(f"Obs: {dd['obs']}")
                    
                    with tabs_det[1]:
                        st.markdown("#### Gerar Proposta")
                        vp = st.number_input("Valor Total", value=ut.safe_float(dd.get('proposta_valor')), min_value=0.0, step=100.0, key="vp")
                        ve = st.number_input("Entrada", value=ut.safe_float(dd.get('proposta_entrada')), min_value=0.0, step=100.0, key="ve")
                        np = st.number_input("Parcelas", value=int(ut.safe_float(dd.get('proposta_parcelas')) or 1), min_value=1, step=1, key="np")
                        pg = st.text_input("Forma Pagamento", value=dd.get('proposta_pagamento', ''), key="pg")
                        ob = st.text_area("Objeto", value=dd.get('proposta_objeto', ''), key="ob")
                        
                        modelos = db.get_modelos_proposta()
                        if not modelos.empty:
                            mod_sel = st.selectbox("Modelo:", modelos['nome_modelo'].tolist())
                            if st.button("Gerar Texto"):
                                id_mod = modelos[modelos['nome_modelo'] == mod_sel].iloc[0]['id']
                                txt = db.gerar_proposta_texto(id_mod, dd)
                                st.text_area("Texto Gerado:", value=txt, height=300)
                        
                        if st.button("💾 Salvar Proposta"):
                            db.crud_update("clientes", {
                                "proposta_valor": vp, "proposta_entrada": ve, "proposta_parcelas": np,
                                "proposta_pagamento": pg, "proposta_objeto": ob
                            }, "id=?", (id_cli,))
                            st.success("Proposta salva!")
                            st.rerun()
                            
                    with tabs_det[2]:
                        if dd['status_cliente'] == 'ATIVO':
                            st.markdown("### 🖨️ Documentos Finais")
                            d1, d2, d3 = st.columns(3)
                            
                            with d1:
                                try:
                                    st.download_button("Procuração", ut.criar_doc("Procuracao", dd), "proc.docx")
                                except ValueError as e: st.error(f"❌ {e}")
                                except Exception as e: st.error("Erro ao gerar Procuração")
                            
                            with d2:
                                try:
                                    st.download_button("Hipossuf.", ut.criar_doc("Hipossuficiencia", dd), "hipo.docx")
                                except ValueError as e: st.error(f"❌ {e}")
                                except Exception as e: st.error("Erro ao gerar Hipossuf.")
                                    
                            with d3:
                                try:
                                    st.download_button("Contrato", ut.criar_doc("Contrato", dd), "cont.docx")
                                except ValueError as e: st.error(f"❌ {e}")
                                except Exception as e: st.error("Erro ao gerar Contrato")
        else:
            st.info("Nenhum cliente cadastrado.")

    # --- ABA 3: KANBAN DE VENDAS ---
    with t3:
        st.markdown("### 📊 Funil de Vendas")
        k1, k2, k3 = st.columns(3)
        df_k = db.sql_get("clientes")
        
        with k1:
            st.info("🟡 Em Negociação")
            if not df_k.empty:
                for _, row in df_k[df_k['status_cliente'] == 'EM NEGOCIAÇÃO'].iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")
                        st.caption(f"R$ {ut.safe_float(row['proposta_valor']):,.2f}")
                        if st.button("➡️ Fechar", key=f"win_{row['id']}"):
                            db.sql_run("UPDATE clientes SET status_cliente='ATIVO' WHERE id=?", (row['id'],))
                            st.rerun()

        with k2:
            st.success("🟢 Fechado / Ativo")
            if not df_k.empty:
                for _, row in df_k[df_k['status_cliente'] == 'ATIVO'].head(10).iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")

        with k3:
            st.error("🔴 Perdido / Inativo")
            if not df_k.empty:
                for _, row in df_k[df_k['status_cliente'] == 'INATIVO'].head(10).iterrows():
                    with st.container(border=True):
                        st.write(f"**{row['nome']}**")
                        if st.button("♻️ Reativar", key=f"react_{row['id']}"):
                            db.sql_run("UPDATE clientes SET status_cliente='EM NEGOCIAÇÃO' WHERE id=?", (row['id'],))
                            st.rerun()

    # --- ABA 4: MODELOS DE PROPOSTA ---
    with t4:
        st.markdown("### 📝 Gerenciar Modelos")
        with st.expander("➕ Criar Novo Modelo"):
            with st.form("form_modelo"):
                mnome = st.text_input("Nome do Modelo")
                mdesc = st.text_input("Descrição")
                mvalor = st.number_input("Valor Sugerido", min_value=0.0)
                mtexto = st.text_area("Texto Padrão", height=200)
                if st.form_submit_button("Salvar"):
                    if mnome and mtexto:
                        db.salvar_modelo_proposta(mnome, mtexto, mdesc, mvalor)
                        st.success("Salvo!")
                        st.rerun()
                    else: st.error("Nome e Texto obrigatórios")
        
        mods = db.get_modelos_proposta()
        if not mods.empty: st.dataframe(mods[['nome_modelo', 'valor_sugerido']], use_container_width=True)

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
            cat = c2.text_input("Categoria")
            desc = st.text_input("Descrição")
            val = st.number_input("Valor (R$)", min_value=0.01)
            c3,c4 = st.columns(2)
            dt = c3.date_input("Data", value=datetime.now())
            resp = c4.selectbox("Responsável", RESPONSAVEIS)
            
            with st.expander("🤝 Parceria / Repasse"):
                tem_parceiro = st.checkbox("Tem Parceiro?")
                perc_parceria = st.number_input("Percentual (%)", value=30.0) if tem_parceiro else 0.0
            
            if st.form_submit_button("Lançar"):
                try:
                    db.crud_insert("financeiro", {
                        "data": dt, "tipo": tipo, "categoria": cat, "descricao": desc,
                        "valor": val, "responsavel": resp, "status_pagamento": "Pendente",
                        "percentual_parceria": perc_parceria
                    })
                    st.success("Lançamento realizado!")
                    st.rerun()
                except Exception as e: st.error(f"Erro: {e}")

    with t2:
        st.markdown("### Extrato")
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
                bx = st.selectbox("Dar Baixa:", lancs['id'].astype(str) + " - " + lancs['descricao'])
                if st.button("Confirmar Pagamento"):
                    lid = int(bx.split(" - ")[0])
                    db.sql_run("UPDATE financeiro SET status_pagamento='Pago' WHERE id=?", (lid,))
                    db.processar_repasse(lid)
                    st.success("Pago!")
                    st.rerun()
        else: st.info("Sem lançamentos.")

    with t3:
        if st.button("Gerar Excel"):
            df = db.sql_get("financeiro")
            if not df.empty:
                path = db.exportar_para_excel(df, f"financeiro_{datetime.now().strftime('%Y%m%d')}")
                with open(path, "rb") as f: st.download_button("Baixar", f, os.path.basename(path))

    with t4:
        st.info("Módulo de parcelamento em desenvolvimento.")

# ==========================================
# 3. PROCESSOS
# ==========================================
elif menu == "Processos":
    st.title("⚖️ Gestão de Processos")
    t1, t2 = st.tabs(["📂 Lista", "➕ Novo"])
    
    with t1:
        df = db.sql_get("processos")
        if not df.empty:
            filtro = st.text_input("🔍 Buscar Processo")
            if filtro: df = df[df['cliente_nome'].str.contains(filtro, case=False) | df['acao'].str.contains(filtro, case=False)]
            st.dataframe(df, use_container_width=True)
            
            sel = st.selectbox("Detalhes:", ["Selecione..."] + (df['id'].astype(str) + " - " + df['cliente_nome']).tolist())
            if sel != "Selecione...":
                pid = int(sel.split(" - ")[0])
                pdados = df[df['id'] == pid].iloc[0]
                st.divider()
                st.subheader(f"Processo #{pid}: {pdados['cliente_nome']}")
                
                tp1, tp2, tp3 = st.tabs(["📅 Andamentos", "📂 Documentos", "💰 Financeiro"])
                
                with tp1:
                    hist = db.get_historico(pid)
                    if not hist.empty: st.dataframe(hist[['data', 'descricao', 'responsavel']])
                    else: st.info("Sem andamentos.")
                    
                    with st.form(f"add_and_{pid}"):
                        desc = st.text_input("Novo Andamento")
                        dt = st.date_input("Data", value=datetime.now())
                        resp = st.selectbox("Responsável", RESPONSAVEIS)
                        if st.form_submit_button("Adicionar"):
                            db.crud_insert("historico_processos", {
                                "id_processo": pid, "data": dt, "descricao": desc, "responsavel": resp
                            })
                            st.success("Adicionado!")
                            st.rerun()
                
                with tp2:
                    st.info("Gestão de documentos em desenvolvimento.")
                
                with tp3:
                    st.info("Financeiro vinculado em desenvolvimento.")
        else: st.info("Nenhum processo cadastrado.")

    with t2:
        st.markdown("### Novo Processo")
        with st.form("form_proc"):
            c1, c2 = st.columns(2)
            cli = c1.selectbox("Cliente", db.sql_get("clientes", "nome")['nome'].tolist() if not db.sql_get("clientes").empty else [])
            acao = c2.text_input("Ação / Título")
            num = st.text_input("Número do Processo")
            vara = st.text_input("Vara / Comarca")
            status = st.selectbox("Status", STATUS_PROCESSO)
            
            if st.form_submit_button("Salvar Processo"):
                if cli and acao:
                    db.crud_insert("processos", {
                        "cliente_nome": cli, "numero_processo": num, "acao": acao,
                        "vara": vara, "status_processo": status, "data_abertura": datetime.now()
                    })
                    st.success("Processo criado!")
                    st.rerun()
                else: st.error("Cliente e Ação obrigatórios")

# ==========================================
# 4. AGENDA
# ==========================================
elif menu == "Agenda":
    st.title("📅 Agenda")
    
    # Adicionar Evento
    with st.expander("➕ Novo Evento"):
        with st.form("evt_form"):
            e_tit = st.text_input("Título")
            c1, c2 = st.columns(2)
            e_ini = c1.date_input("Início", value=datetime.now())
            e_fim = c2.date_input("Fim", value=datetime.now())
            e_resp = st.selectbox("Responsável", RESPONSAVEIS)
            if st.form_submit_button("Agendar"):
                db.crud_insert("agenda", {
                    "titulo": e_tit, "data_inicio": e_ini, "data_fim": e_fim, "responsavel": e_resp
                })
                st.success("Agendado!")
                st.rerun()

    # Visualizar Calendário
    evts = db.get_agenda_eventos()
    calendar_events = []
    for _, row in evts.iterrows():
        calendar_events.append({
            "title": f"{row['titulo']} ({row['responsavel']})",
            "start": row['data_inicio'],
            "end": row['data_fim']
        })
    
    calendar_options = {
        "headerToolbar": {
            "left": "today prev,next",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "initialView": "dayGridMonth",
    }
    try:
        calendar(events=calendar_events, options=calendar_options)
    except: st.warning("Erro ao carregar calendário visual.")

# ==========================================
# 5. IA JURÍDICA
# ==========================================
elif menu == "IA Jurídica":
    st.title("🤖 Assistente Jurídico (Gemini)")
    
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Digite sua dúvida jurídica..."):
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Pensando..."):
                resp = ut.consultar_ia(prompt)
                st.markdown(resp)
                st.session_state.chat_history.append({"role": "assistant", "content": resp})

# ==========================================
# 6. PAINEL GERAL
# ==========================================
elif menu == "Painel Geral":
    st.title("📊 Visão Geral do Escritório")
    
    kpis = db.kpis()
    
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Faturamento Mês", ut.formatar_moeda(kpis['faturamento_mes']))
    k2.metric("Despesas Mês", ut.formatar_moeda(kpis['despesas_mes']))
    k3.metric("Lucro Mês", ut.formatar_moeda(kpis['lucro_mes']), delta_color="normal")
    k4.metric("Processos Ativos", kpis['processos_ativos'])
    
    st.divider()
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Inadimplência")
        st.metric("Total a Receber", ut.formatar_moeda(kpis['inadimplencia_total']))
        
    with c2:
        st.subheader("Backup")
        if st.button("Fazer Backup Manual Agora"):
            res = db.backup_database()
            st.success(f"Backup: {res}")