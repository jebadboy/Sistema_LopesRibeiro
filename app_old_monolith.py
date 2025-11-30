import streamlit as st
from datetime import datetime
import database as db
import utils as ut

st.set_page_config(page_title="Lopes & Ribeiro System", page_icon="⚖️", layout="wide")
db.init_db()

# --- ESTADO DA SESSÃO ---
if 'cliente_ativo' not in st.session_state: st.session_state.cliente_ativo = None
if 'modo_edicao' not in st.session_state: st.session_state.modo_edicao = False

# --- GESTÃO DE ESTADO ---
def inicializar_sessao():
    campos = ['cad_nome', 'cad_cpf', 'cad_email', 'cad_tel', 'cad_fixo', 'cad_prof', 'cad_ec', 'cad_cep', 'cad_rua', 'cad_num', 'cad_comp', 'cad_bairro', 'cad_cid', 'cad_uf', 'cad_obs', 'cad_drive']
    for campo in campos:
        if campo not in st.session_state: st.session_state[campo] = ""

def limpar_campos_cadastro():
    campos = ['cad_nome', 'cad_cpf', 'cad_email', 'cad_tel', 'cad_fixo', 'cad_prof', 'cad_ec', 'cad_cep', 'cad_rua', 'cad_num', 'cad_comp', 'cad_bairro', 'cad_cid', 'cad_uf', 'cad_obs', 'cad_drive']
    for campo in campos:
        st.session_state[campo] = ""

inicializar_sessao()

# --- CALLBACKS ---
def buscar_cep_callback():
    if st.session_state.cad_cep:
        d = ut.buscar_cep(st.session_state.cad_cep)
        if d and "erro" not in d:
            st.session_state.cad_rua = d.get('logradouro', '')
            st.session_state.cad_bairro = d.get('bairro', '')
            st.session_state.cad_cid = d.get('localidade', '')
            st.session_state.cad_uf = d.get('uf', '')
        else: st.toast("CEP não encontrado!", icon="❌")

def salvar_cliente_callback():
    nome = st.session_state.cad_nome; cpf = ut.limpar_numeros(st.session_state.cad_cpf)
    if not nome or not cpf: st.toast("Nome e CPF obrigatórios!", icon="⚠️"); return
    if db.cpf_existe(cpf): st.toast("CPF já cadastrado!", icon="❌"); return
    if not ut.validar_cpf_matematico(cpf): st.toast("CPF Inválido!", icon="❌"); return

    try:
        db.sql_run('''INSERT INTO clientes (nome,cpf_cnpj,email,telefone,telefone_fixo,profissao,estado_civil,cep,endereco,numero_casa,complemento,bairro,cidade,estado,obs,status_cliente,link_drive,data_cadastro) 
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
                   (nome, cpf, st.session_state.cad_email, st.session_state.cad_tel, st.session_state.cad_fixo, 
                    st.session_state.cad_prof, st.session_state.cad_ec, st.session_state.cad_cep, st.session_state.cad_rua, 
                    st.session_state.cad_num, st.session_state.cad_comp, st.session_state.cad_bairro, st.session_state.cad_cid, 
                    st.session_state.cad_uf, st.session_state.cad_obs, st.session_state.cad_stt, st.session_state.cad_drive, 
                    datetime.now().strftime("%Y-%m-%d")))
        st.toast(f"Cliente {nome} Salvo!", icon="✅")
        limpar_campos_cadastro()
    except Exception as e: st.toast(f"Erro: {e}", icon="❌")

# --- CSS ---
st.markdown("""
<style>
    .stApp { background-color: #f8f9fa; }
    div[data-baseweb="input"] > div, div[data-baseweb="select"] > div, div[data-baseweb="textarea"] > div {
        background-color: white !important; border-radius: 8px !important; border: 1px solid #ced4da !important;
    }
    button[kind="primary"] { background-color: #2563eb; border: none; }
    h1, h2, h3 { color: #0f172a !important; }
</style>
""", unsafe_allow_html=True)

# --- MENU ---
with st.sidebar:
    st.title("Lopes & Ribeiro")
    menu = st.radio("Menu", ["Clientes (CRM)", "Financeiro", "Processos", "Painel Geral"])

# ==========================================
# 1. CLIENTES (CRM)
# ==========================================
if menu == "Clientes (CRM)":
    st.title("📂 Gestão de Clientes")
    t1, t2 = st.tabs(["📝 Novo Cadastro", "🔍 Base / Editar / Propostas"])
    
    with t1:
        st.markdown("### 🪪 Identificação")
        c1,c2,c3=st.columns([3,2,1.5])
        c1.text_input("Nome Completo", key="cad_nome")
        c2.text_input("CPF (Só Números)", key="cad_cpf")
        c3.selectbox("Fase", ["EM NEGOCIAÇÃO", "ATIVO"], key="cad_stt")
        
        c4,c5,c6=st.columns(3)
        c4.text_input("E-mail", key="cad_email")
        c5.text_input("WhatsApp", key="cad_tel")
        c6.text_input("Fixo", key="cad_fixo")
        
        c7,c8=st.columns(2)
        c7.text_input("Profissão", key="cad_prof")
        c8.selectbox("Estado Civil", ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"], key="cad_ec")

        st.markdown("### 📍 Endereço")
        cc1,cc2=st.columns([3,1])
        cc1.text_input("CEP", key="cad_cep")
        cc2.button("🔍 Buscar CEP", on_click=buscar_cep_callback)
        
        st.text_input("Logradouro", key="cad_rua")
        e1,e2=st.columns(2)
        e1.text_input("Número", key="cad_num"); e2.text_input("Complemento", key="cad_comp")
        e3,e4,e5=st.columns(3)
        e3.text_input("Bairro", key="cad_bairro"); e4.text_input("Cidade", key="cad_cid"); e5.text_input("UF", key="cad_uf")

        st.markdown("### 📂 Interno")
        st.text_input("Link Drive", key="cad_drive")
        st.text_area("Obs", key="cad_obs")
        
        st.button("💾 SALVAR CLIENTE", type="primary", on_click=salvar_cliente_callback)

    with t2:
        df = db.sql_get("clientes", ordem="nome ASC")
        if not df.empty:
            pesq = st.text_input("🔍 Buscar Cliente:")
            if pesq: df = df[df['nome'].str.contains(pesq, case=False) | df['cpf_cnpj'].str.contains(pesq)]
            
            # CORREÇÃO DO ERRO df_vis
            df_vis = df.copy()
            df_vis['CPF'] = df_vis['cpf_cnpj'].apply(ut.formatar_cpf)
            df_vis['Celular'] = df_vis['telefone'].apply(ut.formatar_celular)
            df_vis['Status'] = df_vis['status_cliente']
            
            opcoes = ["Selecione para Abrir..."] + df['nome'].tolist()
            sel = st.selectbox("Ficha do Cliente:", opcoes)
            
            if sel != "Selecione para Abrir...":
                dd = df[df['nome'] == sel].iloc[0]
                
                with st.container():
                    st.info(f"Cliente: {dd['nome']} | Status: {dd['status_cliente']}")
                    
                    # MODO EDIÇÃO
                    with st.expander("✏️ Editar Dados Cadastrais"):
                        with st.form("edit_form"):
                            enm=st.text_input("Nome", value=dd['nome'])
                            etel=st.text_input("Celular", value=dd['telefone'])
                            efix=st.text_input("Fixo", value=dd['telefone_fixo'])
                            estt=st.selectbox("Status", ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"], index=["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"].index(dd['status_cliente']))
                            eend=st.text_input("Endereço", value=dd['endereco'])
                            if st.form_submit_button("Salvar Alterações"):
                                db.sql_run("UPDATE clientes SET nome=?, telefone=?, telefone_fixo=?, status_cliente=?, endereco=? WHERE id=?", 
                                           (enm, etel, efix, estt, eend, int(dd['id'])))
                                st.success("Atualizado!"); st.rerun()

                    # MODO PROPOSTA
                    with st.expander("💰 Proposta e Negociação", expanded=True):
                        c_p1, c_p2 = st.columns(2)
                        vp = c_p1.number_input("Valor Total (R$)", value=ut.safe_float(dd['proposta_valor']))
                        ve = c_p2.number_input("Entrada (R$)", value=ut.safe_float(dd['proposta_entrada']))
                        c_p3, c_p4 = st.columns(2)
                        np_parc = c_p3.number_input("Parcelas", value=ut.safe_int(dd['proposta_parcelas']))
                        pg_opts = ["PIX", "Dinheiro", "Cartão (TON)", "Parcelado Mensal", "% no Êxito", "Entrada + % Êxito"]
                        pg_val = dd['proposta_pagamento']
                        idx_pg = pg_opts.index(pg_val) if pg_val in pg_opts else 0
                        pg = c_p4.selectbox("Pagamento", pg_opts, index=idx_pg)
                        ob = st.text_area("Objeto (Descrição)", value=dd['proposta_objeto'] if dd['proposta_objeto'] else "")
                        
                        cb1, cb2 = st.columns(2)
                        if cb1.button("💾 Salvar Proposta"):
                            db.sql_run("UPDATE clientes SET proposta_valor=?, proposta_entrada=?, proposta_parcelas=?, proposta_pagamento=?, proposta_objeto=? WHERE id=?", (vp, ve, np_parc, pg, ob, int(dd['id']))); st.success("Salvo!"); st.rerun()
                        with cb2:
                            doc = ut.criar_doc("Proposta", {'nome':dd['nome'], 'proposta_valor':vp, 'proposta_entrada':ve, 'proposta_parcelas':np_parc, 'proposta_objeto':ob, 'proposta_pagamento':pg})
                            st.download_button("📄 Baixar DOC Proposta", doc, f"Prop_{sel}.docx", type="primary")

                    # MODO DOCS FINAIS
                    if dd['status_cliente'] == 'ATIVO':
                        st.markdown("### 🖨️ Documentos Finais")
                        d1, d2, d3 = st.columns(3)
                        with d1: st.download_button("Procuração", ut.criar_doc("Procuracao", dd), "proc.docx")
                        with d2: st.download_button("Hipossuf.", ut.criar_doc("Hipossuficiencia", dd), "hipo.docx")
                        with d3: st.download_button("Contrato", ut.criar_doc("Contrato", dd), "cont.docx")

                    if st.button("🗑️ Excluir Cliente"):
                        db.sql_run("DELETE FROM clientes WHERE id=?", (int(dd['id']),)); st.rerun()

            st.dataframe(df_vis[['nome','CPF','Celular','Status']], use_container_width=True)
        else: st.info("Nenhum cliente.")

# ==========================================
# 2. FINANCEIRO (COM RECIBOS)
# ==========================================
elif menu == "Financeiro":
    st.title("💰 Finanças")
    t1, t2 = st.tabs(["Lançar", "Extrato"])
    with t1:
        dfc = db.sql_get("clientes")
        l = ["Avulso"] + dfc['nome'].tolist() if not dfc.empty else ["Avulso"]
        with st.container():
            c1,c2=st.columns(2); dt=c1.date_input("Vencimento"); tp=c2.selectbox("Tipo",["Entrada","Saída"])
            cl=st.selectbox("Cliente",l); dc=st.text_input("Descrição"); v=st.number_input("Valor R$", min_value=0.0)
            stt=st.selectbox("Status",["Pago","Pendente"]); rp=st.selectbox("Resp",["Eduardo","Sheila"])
            if st.button("Lançar Financeiro", type="primary"):
                db.sql_run("INSERT INTO financeiro (data,tipo,categoria,descricao,valor,responsavel,status_pagamento,vencimento) VALUES (?,?,?,?,?,?,?,?)",(dt,tp,"Geral",f"{cl}-{dc}",v,rp,stt,dt)); st.success("Lançado!")
    with t2:
        df=db.sql_get("financeiro")
        if not df.empty:
            st.dataframe(df.sort_values(by="data",ascending=False), use_container_width=True)
            try: st.download_button("📥 Excel", ut.to_excel(df), "fin.xlsx")
            except: pass
            st.divider()
            ents=df[df['tipo']=='Entrada']; df['lbl']=df['id'].astype(str)+" - "+df['descricao']
            sl=st.selectbox("Gerar Recibo para:", ents['lbl'].tolist())
            if sl: 
                dd=df[df['id']==int(sl.split(" - ")[0])].iloc[0]; nm=dd['descricao'].split("-")[0]
                st.download_button("📄 Baixar Recibo", ut.criar_doc("Recibo", {'cliente_nome':nm,'valor':dd['valor'],'descricao':dd['descricao']}), "rec.docx")

# ==========================================
# 3. PROCESSOS (COM HISTÓRICO)
# ==========================================
elif menu == "Processos":
    st.title("⚖️ Processos")
    t1, t2 = st.tabs(["Novo (+Calc)", "Gerenciar"])
    with t1:
        st.markdown("#### 🧠 Calculadora de Prazos")
        c1,c2,c3=st.columns(3); dp=c1.date_input("Publicação"); di=c2.number_input("Dias",15); rg=c3.selectbox("Regra",["Dias Úteis","Corridos"])
        vc=ut.calc_venc(dp,di,rg); st.info(f"📅 Fatal: {vc.strftime('%d/%m/%Y')}")
        st.divider()
        with st.form("np"):
            l=db.sql_get("clientes")['nome'].tolist() if not db.sql_get("clientes").empty else []
            cl=st.selectbox("Cli",l); ac=st.text_input("Ação"); pz=st.date_input("Prazo",value=vc)
            if st.form_submit_button("Salvar"): db.sql_run("INSERT INTO processos (cliente_nome,acao,proximo_prazo,responsavel,status) VALUES (?,?,?,?,?)",(cl,ac,pz,"Eduardo","Ativo")); st.success("Salvo!")
    with t2:
        df=db.sql_get("processos")
        if not df.empty:
            df['Farol']=df['proximo_prazo'].apply(ut.calcular_farol)
            st.dataframe(df[['Farol','cliente_nome','acao','proximo_prazo']], use_container_width=True)
            df['lbl'] = df['cliente_nome'] + " - " + df['acao']; sel_p = st.selectbox("Selecione:", df['lbl'].unique())
            if sel_p:
                pid = int(df[df['lbl']==sel_p].iloc[0]['id']); hist = db.get_historico(pid); st.table(hist) if not hist.empty else st.caption("Sem andamentos.")
                with st.form("nad"): 
                    dt=st.date_input("Data"); ds=st.text_input("Ocorrencia"); 
                    if st.form_submit_button("Registrar Andamento"): db.sql_run("INSERT INTO andamentos (id_processo,data,descricao,responsavel) VALUES (?,?,?,?)",(pid,dt,ds,"Sys")); st.rerun()
            try: st.download_button("📥 Excel", ut.to_excel(df), "proc.xlsx")
            except: pass

# 4. PAINEL GERAL
elif menu == "Painel Geral":
    st.title("📊 Painel de Controle")
    s, r, nc, np = db.kpis() if hasattr(db, 'kpis') else (0,0,0,0)
    f=db.sql_get("financeiro"); c=db.sql_get("clientes"); p=db.sql_get("processos")
    s=0; r=0; nc=len(c[c['status_cliente']=='ATIVO']) if not c.empty else 0; np=len(p) if not p.empty else 0
    if not f.empty:
        s = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pago')]['valor'].sum() - f[(f['tipo']=='Saída')&(f['status_pagamento']=='Pago')]['valor'].sum()
        r = f[(f['tipo']=='Entrada')&(f['status_pagamento']=='Pendente')]['valor'].sum()
    c1,c2,c3,c4=st.columns(4); c1.metric("Caixa",ut.formatar_moeda(s)); c2.metric("Receber",ut.formatar_moeda(r)); c3.metric("Clientes",nc); c4.metric("Processos",np)
    st.divider()
    with open("dados_escritorio.db", "rb") as fp: st.download_button("💾 Backup Completo", fp, "bkp.db")