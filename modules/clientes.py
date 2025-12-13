import streamlit as st
import re
import math
import logging
import pandas as pd
from datetime import datetime, date
from typing import Optional, Dict, Any, Union
import time

import database as db
import utils as ut
import google_drive as gd
import crypto  # Módulo de criptografia LGPD
import token_manager as tm
import utils_email
import email_templates
from components.cliente_styles import get_cliente_css

logger = logging.getLogger(__name__)

# --- CONSTANTES ---
OPCOES_STATUS = ["EM NEGOCIAÇÃO", "ATIVO", "INATIVO"]
OPCOES_TIPO_PESSOA = ["Física", "Jurídica"]  # CORRIGIDO: era "Juríddica"
OPCOES_ESTADO_CIVIL = ["Casado(a)", "Solteiro(a)", "Divorciado(a)", "Viúvo(a)", "União Estável"]
OPCOES_PAGAMENTO = ["PIX", "Dinheiro", "Cartão (TON)", "Parcelado Mensal", "% no Êxito", "Entrada + % Êxito"]

# Constantes de configuração
LINKS_GRID_COLUMNS = 3  # Número de colunas para grid de links
DIAS_SEM_CONTATO_ALERTA_AMARELO = 30
DIAS_SEM_CONTATO_ALERTA_LARANJA = 60
DIAS_SEM_CONTATO_ALERTA_VERMELHO = 90

# Regex robusto para validação de e-mail (RFC 5322 simplificado)
EMAIL_REGEX = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'

def maskear_cpf(cpf):
    """
    Mascara CPF para logs (LGPD)
    Exemplo: '12345678901' -> '***456***01'
    """
    if not cpf or len(str(cpf)) < 4:
        return '***'
    cpf_str = str(cpf)
    return f"***{cpf_str[-6:-2]}***{cpf_str[-2:]}"

def safe_get(series_or_dict, key, default=None):
    """Extrai valor escalar de Series/dict de forma segura"""
    if isinstance(series_or_dict, dict):
        return series_or_dict.get(key, default)
    
    value = series_or_dict.get(key, default)
    # Se retornou uma Series (colunas duplicadas), pega o primeiro
    if hasattr(value, 'iloc'):
        return value.iloc[0] if len(value) > 0 else default
    return value if value is not None else default

def formatar_campo(key, func):
    """Callback genérico para formatar campos."""
    if key in st.session_state:
        valor = st.session_state[key]
        st.session_state[key] = func(valor)

def decrypt_cpf_safe(cpf_cnpj: str) -> str:
    """
    Descriptografa CPF/CNPJ de forma segura (SPRINT 2 - #M4)
    
    Args:
        cpf_cnpj: CPF/CNPJ potencialmente criptografado
        
    Returns:
        CPF/CNPJ descriptografado ou "***ERRO***" em caso de falha
        
    Example:
        >>> cpf = decrypt_cpf_safe("ENC:abc123...")
        >>> # Retorna CPF descriptografado
    """
    try:
        if cpf_cnpj and str(cpf_cnpj).startswith('ENC:'):
            return crypto.decrypt(cpf_cnpj)
        return cpf_cnpj or ""
    except Exception as e:
        # LGPD: Não logar CPF aqui, apenas indicar erro
        logger.error(f"Erro ao descriptografar documento: {type(e).__name__}")
        return "***ERRO***"


def render():
    st.markdown(get_cliente_css(), unsafe_allow_html=True)
    st.markdown("<h1 style='color: var(--text-main);'>📂 Gestão de Clientes</h1>", unsafe_allow_html=True)

    # Tabs com design limpo
    t1, t2 = st.tabs(["📝 Novo Cadastro", "🔍 Base / Editar / Propostas"])
    
    # --- ABA 1: NOVO CADASTRO ---
    with t1:
        render_novo_cadastro()

    # --- ABA 2: GESTÃO ---
    with t2:
        render_gestao_clientes()

def render_campos_identificacao(prefixo, dados=None, status_args=None):
    """Renderiza campos de identificação (Nome, CPF/CNPJ, Tipo)"""
    dados = dados or {}
    status_args = status_args or {}
    
    # Linha 1: Tipo e Status (se fornecido)
    # Se tiver status, dividimos. Se não, só tipo.
    if status_args:
        c_top1, c_top2 = st.columns([1, 1])
        with c_top1:
             tipo_key = f"{prefixo}_tipo_pessoa"
             tipo_valor = safe_get(dados, 'tipo_pessoa', 'Física')
             tipo_pessoa = st.radio("Tipo de Pessoa", OPCOES_TIPO_PESSOA, 
                                   index=0 if tipo_valor == "Física" else 1,
                                   horizontal=True, key=tipo_key)
        with c_top2:

            st_key = status_args.get('key')
            st_opts = status_args.get('options', [])
            st_idx = status_args.get('index', 0)
            
            # Inicializar session_state com validação de índice
            if st_key and st_key not in st.session_state:
                 # Se o index aponta, temos que achar o valor
                 if 0 <= st_idx < len(st_opts):
                     st.session_state[st_key] = st_opts[st_idx]
                 else:
                     # Fallback seguro para primeiro item
                     st.session_state[st_key] = st_opts[0] if st_opts else None
                     logger.warning(f"Índice inválido {st_idx} para opções de status, usando fallback")
            
            st.selectbox("Status / Fase", options=st_opts, key=st_key)
    else:
        tipo_key = f"{prefixo}_tipo_pessoa"
        tipo_valor = safe_get(dados, 'tipo_pessoa', 'Física')
        tipo_pessoa = st.radio("Tipo de Pessoa", OPCOES_TIPO_PESSOA, 
                              index=0 if tipo_valor == "Física" else 1,
                              horizontal=True, key=tipo_key)

    # Linha 2: Nome e Doc
    c1, c2 = st.columns([2, 1])
    c1.text_input("Nome Completo / Razão Social", value=safe_get(dados, 'nome', ''), key=f"{prefixo}_nome")
    
    label_doc = "CPF (Só Números)" if tipo_pessoa == "Física" else "CNPJ (Só Números)"
    doc_key = f"{prefixo}_cpf_cnpj"
    c2.text_input(label_doc, value=safe_get(dados, 'cpf_cnpj', ''), key=doc_key, max_chars=18,
                  on_change=formatar_campo, args=(doc_key, ut.formatar_documento))
    
    return tipo_pessoa

def render_campos_contato(prefixo, dados=None):
    """Renderiza campos de contato e perfil em layout compacto"""
    dados = dados or {}
    
    # Linha 1: Email, Celular, Fixo
    c1, c2, c3 = st.columns([2, 1, 1])
    c1.text_input("E-mail", value=safe_get(dados, 'email', ''), key=f"{prefixo}_email")
    
    tel_key = f"{prefixo}_tel"
    c2.text_input("WhatsApp/Celular", value=safe_get(dados, 'telefone', ''), key=tel_key, max_chars=15,
                   on_change=formatar_campo, args=(tel_key, ut.formatar_celular))
    
    fixo_key = f"{prefixo}_fixo"
    c3.text_input("Fixo", value=safe_get(dados, 'telefone_fixo', ''), key=fixo_key, max_chars=14,
                   on_change=formatar_campo, args=(fixo_key, ut.formatar_celular))

    # Linha 2: Profissão, Estado Civil
    c4, c5 = st.columns([1.5, 1])
    c4.text_input("Profissão / Ramo de Atividade", value=safe_get(dados, 'profissao', ''), key=f"{prefixo}_prof")
    
    opcoes_ec = list(OPCOES_ESTADO_CIVIL)
    valor_ec = safe_get(dados, 'estado_civil', 'Solteiro(a)')
    key_ec = f"{prefixo}_ec"
    
    # Se valor não estiver nas opções padrão, adiciona
    if valor_ec not in opcoes_ec: opcoes_ec.insert(0, valor_ec)
    

    # Inicializar session_state para evitar warning de default value vs session state
    if key_ec not in st.session_state:
        st.session_state[key_ec] = valor_ec

    c5.selectbox("Estado Civil", opcoes_ec, key=key_ec)

def render_campos_pessoais_fisica(prefixo, dados=None):
    """Renderiza campos específicos de Pessoa Física"""
    dados = dados or {}
    
    # Grid de 4 colunas para otimizar espaço vertical
    c1, c2, c3, c4 = st.columns([1, 1, 1, 1])
    
    rg_key = f"{prefixo}_rg"
    c1.text_input("RG", value=safe_get(dados, 'rg', ''), key=rg_key, max_chars=12,
                 on_change=formatar_campo, args=(rg_key, ut.formatar_rg))
    
    c2.text_input("Órgão Emissor", value=safe_get(dados, 'orgao_emissor', ''), key=f"{prefixo}_orgao_emissor")
    c3.text_input("Nacionalidade", value=safe_get(dados, 'nacionalidade', ''), key=f"{prefixo}_nacionalidade")
    
    # Data de Nascimento com tratamento robusto de erro
    data_valor = None
    data_nasc = safe_get(dados, 'data_nascimento')
    if data_nasc:
        try:
            if isinstance(data_nasc, str):
                data_valor = datetime.strptime(data_nasc, '%Y-%m-%d').date()
            elif isinstance(data_nasc, date):
                data_valor = data_nasc
            elif isinstance(data_nasc, datetime):
                data_valor = data_nasc.date()
            else:
                logger.warning(f"Tipo inesperado para data de nascimento: {type(data_nasc)}")
                data_valor = None
        except (ValueError, TypeError) as e:
            logger.warning(f"Data de nascimento inválida '{data_nasc}': {e}")
            data_valor = None
    
    c4.date_input("Nascimento", value=data_valor, key=f"{prefixo}_data_nascimento", format="DD/MM/YYYY", 
                  min_value=date(1900, 1, 1), max_value=date(2100, 12, 31))

def render_campos_endereco(prefixo, dados=None):
    """Renderiza campos de endereço compactados"""
    dados = dados or {}
    
    # Callback especial para buscar CEP
    def buscar_cep_wrapper():
        # SPRINT 2 - #S3: Rate limiting para evitar abuso da API
        rate_limit_key = f"ultimo_cep_busca_{prefixo}"
        ultimo_tempo = st.session_state.get(rate_limit_key, 0)
        tempo_atual = time.time()
        
        # Limitar a 1 busca por segundo
        if tempo_atual - ultimo_tempo < 1.0:
            st.toast("⚠️ Aguarde 1 segundo entre buscas de CEP", icon="⏱️")
            return
        
        st.session_state[rate_limit_key] = tempo_atual
        
        cep_val = st.session_state.get(f"{prefixo}_cep")
        if cep_val:
            d = ut.buscar_cep(cep_val)
            if d and "erro" not in d:
                st.session_state[f"{prefixo}_rua"] = d.get('logradouro', '')
                st.session_state[f"{prefixo}_bairro"] = d.get('bairro', '')
                st.session_state[f"{prefixo}_cid"] = d.get('localidade', '')
                st.session_state[f"{prefixo}_uf"] = d.get('uf', '')
            else: 
                st.toast("CEP não encontrado!", icon="❌")

    # Linha 1: CEP + Botão + Logradouro
    c_l1_1, c_l1_2, c_l1_3 = st.columns([1.2, 0.5, 3])
    cep_key = f"{prefixo}_cep"
    c_l1_1.text_input("CEP", value=safe_get(dados, 'cep', ''), key=cep_key, max_chars=9, label_visibility="visible",
                   on_change=formatar_campo, args=(cep_key, ut.formatar_cep))
    c_l1_2.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True) # Espaçador visual
    c_l1_2.button("🔍", key=f"btn_cep_{prefixo}", on_click=buscar_cep_wrapper, help="Buscar CEP")
    
    c_l1_3.text_input("Logradouro", value=safe_get(dados, 'endereco', ''), key=f"{prefixo}_rua")
    
    # Linha 2: Num, Compl, Bairro, Cid, UF
    c_l2_1, c_l2_2, c_l2_3, c_l2_4, c_l2_5 = st.columns([1, 1.5, 2, 2, 0.8])
    c_l2_1.text_input("Número", value=safe_get(dados, 'numero_casa', ''), key=f"{prefixo}_num")
    c_l2_2.text_input("Complemento", value=safe_get(dados, 'complemento', ''), key=f"{prefixo}_comp")
    c_l2_3.text_input("Bairro", value=safe_get(dados, 'bairro', ''), key=f"{prefixo}_bairro")
    c_l2_4.text_input("Cidade", value=safe_get(dados, 'cidade', ''), key=f"{prefixo}_cid")
    c_l2_5.text_input("UF", value=safe_get(dados, 'estado', ''), key=f"{prefixo}_uf")

def render_novo_cadastro():
    # st.markdown("### 📝 Novo Cadastro") # Opcional, já está na aba
    
    # 1. Identificação - Card
    with st.container(border=True):
        st.markdown("**🪪 Identificação**")
        status_opts = {"options": OPCOES_STATUS, "key": "cad_stt", "index": 0}
        tipo_pessoa = render_campos_identificacao("cad", status_args=status_opts)
    
    # 2. Contato e Pessoais - Card
    with st.container(border=True):
        st.markdown("**📞 Contato & Dados**")
        render_campos_contato("cad")
        
        if tipo_pessoa == "Física":
            st.markdown("---")
            render_campos_pessoais_fisica("cad")
        else:
            # Limpar campos ocultos
            st.session_state.setdefault("cad_rg", "")
            st.session_state.setdefault("cad_orgao_emissor", "")
            st.session_state.setdefault("cad_nacionalidade", "")
            st.session_state.setdefault("cad_data_nascimento", None)

    # 3. Endereço - Card
    with st.container(border=True):
         st.markdown("**📍 Endereço**")
         render_campos_endereco("cad")

    # 4. Interno
    with st.container(border=True):
         st.markdown("**📂 Interno**")
         st.text_input("Link Drive", key="cad_drive", help="Link Google Drive")
         st.text_area("Obs", key="cad_obs", height=68)
    
    # 5. Consentimento LGPD (Obrigatório)
    with st.container(border=True):
         st.markdown("**🔐 Proteção de Dados (LGPD)**")
         st.caption("Conforme Lei nº 13.709/2018, o cliente deve consentir com o tratamento dos seus dados pessoais.")
         st.checkbox(
             "✅ Declaro que obtive consentimento do cliente para armazenar e tratar seus dados pessoais para fins de prestação de serviços jurídicos.",
             key="cad_lgpd",
             value=False
         )
         st.button("💾 SALVAR CADASTRO", type="primary", on_click=salvar_cliente_callback, use_container_width=True)


def render_gestao_clientes():
    df = db.sql_get("clientes", order_by="nome ASC")
    
    # Prevenir erro de colunas duplicadas que causa "Series is ambiguous"
    if not df.empty:
        df = df.loc[:, ~df.columns.duplicated()]

    if df.empty:
        st.info("Nenhum cliente cadastrado.")
        return
    
    # --- MÉTRICAS NO TOPO ---
    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    
    total_clientes = len(df)
    ativos = len(df[df['status_cliente'] == 'ATIVO'])
    em_negociacao = len(df[df['status_cliente'] == 'EM NEGOCIAÇÃO'])
    inativos = len(df[df['status_cliente'] == 'INATIVO'])
    
    col_m1.metric("👥 Total", total_clientes)
    col_m2.metric("✅ Ativos", ativos)
    col_m3.metric("🔔 Negociação", em_negociacao)
    col_m4.metric("⏸️ Inativos", inativos)
    
    st.markdown("---")
    
    # --- FILTROS AVANÇADOS ---
    with st.expander("🔍 Filtros Avançados", expanded=False):
        col_f1, col_f2, col_f3 = st.columns(3)
        
        # Filtro por Status
        filtro_status = col_f1.multiselect(
            "Status",
            options=["ATIVO", "EM NEGOCIAÇÃO", "INATIVO"],
            default=[]
        )
        
        # Filtro por Cidade (dinâmico)
        cidades_unicas = df['cidade'].dropna().unique().tolist()
        filtro_cidade = col_f2.multiselect(
            "Cidade",
            options=sorted(cidades_unicas),
            default=[]
        )
        
        # Filtro por Tipo de Pessoa
        filtro_tipo = col_f3.multiselect(
            "Tipo",
            options=["Física", "Jurídica"],
            default=[]
        )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if filtro_status:
        df_filtrado = df_filtrado[df_filtrado['status_cliente'].isin(filtro_status)]
    
    if filtro_cidade:
        df_filtrado = df_filtrado[df_filtrado['cidade'].isin(filtro_cidade)]
    
    if filtro_tipo:
        df_filtrado = df_filtrado[df_filtrado['tipo_pessoa'].isin(filtro_tipo)]
    
    # Busca por texto (SPRINT 3 - #F1: Incluir e-mail na busca)
    pesq = st.text_input("🔍 Buscar Cliente (Nome, CPF, CNPJ ou E-mail):", key="busca_cliente")
    if pesq:
        # Tratamento de NaN para evitar erros na busca
        df_filtrado = df_filtrado[
            (df_filtrado['nome'].fillna('').str.contains(pesq, case=False)) | 
            (df_filtrado['cpf_cnpj'].fillna('').str.contains(pesq)) |
            (df_filtrado['email'].fillna('').str.contains(pesq, case=False))  # ← NOVO: busca por email
        ]
    
    # --- PAGINAÇÃO ---
    ITENS_POR_PAGINA = 20
    total_registros = len(df_filtrado)
    total_paginas = max(1, (total_registros + ITENS_POR_PAGINA - 1) // ITENS_POR_PAGINA)
    
    # Controle de página no session_state
    if 'pagina_atual' not in st.session_state:
        st.session_state.pagina_atual = 1
    
    # Resetar página se filtros mudarem
    if st.session_state.pagina_atual > total_paginas:
        st.session_state.pagina_atual = 1
    
    # Calcular índices de slice
    inicio = (st.session_state.pagina_atual - 1) * ITENS_POR_PAGINA
    fim = inicio + ITENS_POR_PAGINA
    
    df_pagina = df_filtrado.iloc[inicio:fim]
    
    # Preparar DataFrame para visualização
    df_vis = df_pagina.copy()
    
    # Formatação segura de documentos (descriptografar se necessário)
    def formatar_doc_seguro(cpf_cnpj):
        """Descriptografa e formata documento de forma segura"""
        try:
            # SPRINT 2 - #M4: Usar helper
            cpf_descriptografado = decrypt_cpf_safe(cpf_cnpj)
            return ut.formatar_documento(cpf_descriptografado)
        except Exception as e:
            logger.error(f"Erro ao formatar CPF/CNPJ: {e}")
            return "***ERRO***"
    
    df_vis['Documento'] = df_vis['cpf_cnpj'].apply(formatar_doc_seguro)
    df_vis['Celular'] = df_vis['telefone'].apply(ut.formatar_celular)
    df_vis['Status'] = df_vis['status_cliente']
    
    # Adicionar coluna de link para o Drive
    df_vis['Drive'] = df_vis['link_drive'].astype(str).str.strip()
    # Converter vazios/nan para None para não gerar links quebrados
    df_vis.loc[df_vis['Drive'].isin(['', 'nan', 'None']), 'Drive'] = None

    # --- SELEÇÃO DE CLIENTE ---
    opcoes = ["Selecione para Abrir..."] + df_filtrado['nome'].tolist()
    sel = st.selectbox("Ficha do Cliente:", opcoes, key="select_cliente")
    
    if sel != "Selecione para Abrir...":
        dd = df_filtrado[df_filtrado['nome'] == sel].iloc[0]
        # Garantir unicidade do índice para evitar Series ambígua
        if hasattr(dd, 'index') and dd.index.duplicated().any():
            dd = dd[~dd.index.duplicated(keep='first')]
        
        # LGPD: Registrar acesso a dados pessoais
        try:
            db.log_acesso_dados("clientes", int(dd['id']), "VIEW")
        except Exception as e:
            logger.warning(f"Falha ao registrar log de acesso LGPD: {e}")
        
        # SOLUÇÃO DEFINITIVA: Converter Series para dict para eliminar qualquer ambiguidade
        dd_dict = dd.to_dict()
        render_ficha_cliente(dd_dict)

    st.markdown("### Base de Clientes")
    
    # Informação de paginação e botão de exportação
    col_info, col_export = st.columns([3, 1])
    
    with col_info:
        st.caption(f"Mostrando {len(df_pagina)} de {total_registros} clientes | Página {st.session_state.pagina_atual} de {total_paginas}")
    
    with col_export:
        # Botão de exportação Excel
        if st.button("📄 Exportar Excel", use_container_width=True):
            # Preparar dados para exportação (todos os filtrados, não apenas a página)
            df_export = df_filtrado.copy()
            df_export['Documento'] = df_export['cpf_cnpj'].apply(formatar_doc_seguro)
            df_export['Celular'] = df_export['telefone'].apply(ut.formatar_celular)
            
            # Selecionar colunas relevantes
            colunas_export = ['nome', 'Documento', 'email', 'Celular', 'telefone_fixo', 
                            'cidade', 'estado', 'status_cliente', 'data_cadastro']
            df_export_final = df_export[colunas_export]
            
            # Renomear colunas para português
            df_export_final.columns = ['Nome', 'CPF/CNPJ', 'E-mail', 'Celular', 'Fixo', 
                                       'Cidade', 'UF', 'Status', 'Data Cadastro']
            
            # Converter para Excel em memória
            from io import BytesIO
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df_export_final.to_excel(writer, index=False, sheet_name='Clientes')
            excel_data = output.getvalue()
            
            # Download
            st.download_button(
                label="⬇️ Baixar Excel",
                data=excel_data,
                file_name=f"clientes_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
    
    # Configuração das colunas para o Dataframe
    st.dataframe(
        df_vis[['nome', 'Documento', 'Celular', 'Status', 'Drive']], 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Drive": st.column_config.LinkColumn(
                "Drive",
                help="Clique para abrir a pasta do Drive",
                display_text="📂 Abrir"
            )
        }
    )
    
    # Controles de paginação
    if total_paginas > 1:
        col_prev, col_page_info, col_next = st.columns([1, 2, 1])
        
        with col_prev:
            if st.button("⬅️ Anterior", disabled=st.session_state.pagina_atual == 1, use_container_width=True):
                st.session_state.pagina_atual -= 1
                st.rerun()
        
        with col_page_info:
            # Seletor de página
            nova_pagina = st.selectbox(
                "Ir para página:",
                range(1, total_paginas + 1),
                index=st.session_state.pagina_atual - 1,
                key="page_selector"
            )
            if nova_pagina != st.session_state.pagina_atual:
                st.session_state.pagina_atual = nova_pagina
                st.rerun()
        
        with col_next:
            if st.button("Próxima ➡️", disabled=st.session_state.pagina_atual == total_paginas, use_container_width=True):
                st.session_state.pagina_atual += 1
                st.rerun()
    
    # Hack para tornar o ícone clicável na tabela (se o Streamlit suportar LinkColumn corretamente com dados do DF)
    # Caso contrário, o usuário pode copiar o link da ficha.

def render_ficha_cliente(dd_cru):
    # Descriptografar dados sensíveis antes de exibir
    dd = dd_cru.copy()
    
    # SPRINT 2 - #M4: Usar helper (descriptografia segura com tratamento de erro)
    dd['cpf_cnpj'] = decrypt_cpf_safe(dd.get('cpf_cnpj', ''))

    # Card de Cabeçalho
    tipo = safe_get(dd, 'tipo_pessoa', 'Física')
    doc_formatado = ut.formatar_documento(safe_get(dd, 'cpf_cnpj'), tipo)
    
    drive_link_html = ""
    link_drive = safe_get(dd, 'link_drive')
    if link_drive:
        drive_link_html = f"""<a href="{link_drive}" target="_blank" style="text-decoration: none; font-size: 1.2em;">📂 Abrir Pasta no Drive</a>"""

    st.markdown(f"""
    <div class="metric-card" style="border-left-color: var(--primary); margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align_items: center;">
            <div class="metric-value">{safe_get(dd, 'nome')}</div>
            <div>{drive_link_html}</div>
        </div>
        <div class="metric-label">Status: {safe_get(dd, 'status_cliente')} | {tipo}: {doc_formatado}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # Card de resumo moderno
    render_cliente_card(dd)
    
    # Timeline de histórico
    st.markdown("### 🛤️ Histórico do Cliente")
    render_timeline_avancada(safe_get(dd, 'id'))
    
    st.divider()
    
    # AÇÕES RÁPIDAS
    c_act1, c_act2 = st.columns(2)
    if c_act1.button("➕ Novo Processo", use_container_width=True):
        st.session_state.pre_fill_client = safe_get(dd, 'nome')
        st.session_state.next_nav = "Processos"
        st.rerun()
        
    if c_act2.button("💰 Novo Lançamento", use_container_width=True):
        st.session_state.pre_fill_client = safe_get(dd, 'nome')
        st.session_state.next_nav = "Financeiro"
        st.rerun()
    
    st.divider()
    
    # MODO EDIÇÃO COMPLETA
    with st.expander("✏️ Editar Dados Cadastrais", expanded=False):
        prefixo_edit = f"edit_{safe_get(dd, 'id')}"
        
        # 1. Identificação - Card
        with st.container(border=True):
            st.markdown("**🪪 Identificação**")
            current_status = safe_get(dd, 'status_cliente')
            if hasattr(current_status, 'iloc'): current_status = current_status.iloc[0]
            opcoes_status = OPCOES_STATUS
            idx_status = opcoes_status.index(current_status) if current_status in opcoes_status else 0
            
            status_opts = {"options": opcoes_status, "key": f"{prefixo_edit}_stt", "index": idx_status}
            tipo_pessoa_edit = render_campos_identificacao(prefixo_edit, dd, status_args=status_opts)
        
        # 2. Contato - Card
        with st.container(border=True):
            st.markdown("**📞 Contato & Dados**")
            render_campos_contato(prefixo_edit, dd)
            
            if tipo_pessoa_edit == "Física":
                st.markdown("---")
                render_campos_pessoais_fisica(prefixo_edit, dd)
                
        # 3. Endereço - Card
        with st.container(border=True):
            st.markdown("**📍 Endereço**")
            render_campos_endereco(prefixo_edit, dd)
            
        # 4. Interno e Salvar
        with st.container(border=True):
            st.markdown("**📂 Interno**")
            st.text_input("Link Drive", value=safe_get(dd, 'link_drive', ''), key=f"{prefixo_edit}_drive")
            st.text_area("Observações", value=safe_get(dd, 'obs', ''), key=f"{prefixo_edit}_obs")
            
            if st.button("💾 Salvar Alterações", type="primary", key=f"btn_save_{safe_get(dd, 'id')}"):
                # Recuperar valores e salvar (Lógica similar, apenas recuperando do session_state)
                p = prefixo_edit
                enm = st.session_state.get(f"{p}_nome")
                etipo = st.session_state.get(f"{p}_tipo_pessoa")
                edoc = st.session_state.get(f"{p}_cpf_cnpj")
                estt = st.session_state.get(f"{p}_stt")
                eemail = st.session_state.get(f"{p}_email")
                etel = st.session_state.get(f"{p}_tel")
                efix = st.session_state.get(f"{p}_fixo")
                eprof = st.session_state.get(f"{p}_prof")
                eec = st.session_state.get(f"{p}_ec")
                
                erg = st.session_state.get(f"{p}_rg", "")
                eorgao = st.session_state.get(f"{p}_orgao_emissor", "")
                enac = st.session_state.get(f"{p}_nacionalidade", "")
                edata_nasc = st.session_state.get(f"{p}_data_nascimento")
                
                ecep = st.session_state.get(f"{p}_cep")
                erua = st.session_state.get(f"{p}_rua")
                enum = st.session_state.get(f"{p}_num")
                ecomp = st.session_state.get(f"{p}_comp")
                ebairro = st.session_state.get(f"{p}_bairro")
                ecid = st.session_state.get(f"{p}_cid")
                euf = st.session_state.get(f"{p}_uf")
                
                edrive = st.session_state.get(f"{p}_drive")
                eobs = st.session_state.get(f"{p}_obs")

                data_nasc_str = None
                if edata_nasc:
                    data_nasc_str = edata_nasc.strftime("%Y-%m-%d")
                
                # Criptografar documento (LGPD)
                edoc_save = edoc
                if edoc and not str(edoc).startswith('ENC:'):
                    edoc_save = crypto.encrypt(edoc)

                db.sql_run("""
                    UPDATE clientes SET 
                    nome=?, tipo_pessoa=?, cpf_cnpj=?, status_cliente=?, email=?, telefone=?, telefone_fixo=?, 
                    profissao=?, estado_civil=?, cep=?, endereco=?, numero_casa=?, complemento=?, 
                    bairro=?, cidade=?, estado=?, link_drive=?, obs=?, 
                    rg=?, orgao_emissor=?, nacionalidade=?, data_nascimento=?
                    WHERE id=?
                """, (enm, etipo, edoc_save, estt, eemail, etel, efix, eprof, eec, ecep, erua, enum, ecomp, ebairro, ecid, euf, edrive, eobs, erg, eorgao, enac, data_nasc_str, int(safe_get(dd, 'id'))))
                
                st.success("Dados atualizados com sucesso!")
                st.rerun()

    # MODO PROPOSTA
    with st.expander("💰 Proposta e Negociação", expanded=True):
        c_p1, c_p2 = st.columns(2)
        vp = c_p1.number_input("Valor Total (R$)", value=ut.safe_float(safe_get(dd, 'proposta_valor')))
        ve = c_p2.number_input("Entrada (R$)", value=ut.safe_float(safe_get(dd, 'proposta_entrada')))
        
        c_p3, c_p4 = st.columns(2)
        np_parc = c_p3.number_input("Parcelas", value=ut.safe_int(safe_get(dd, 'proposta_parcelas')))
        
        pg_opts = OPCOES_PAGAMENTO
        pg_val = safe_get(dd, 'proposta_pagamento')
        idx_pg = pg_opts.index(pg_val) if pg_val in pg_opts else 0
        pg = c_p4.selectbox("Pagamento", pg_opts, index=idx_pg)
        
        # Data de Pagamento (se parcelado)
        data_pag = None
        if pg == "Parcelado Mensal":
            val_data = dd.get('proposta_data_pagamento')
            if val_data:
                try:
                    val_data = datetime.strptime(val_data, '%Y-%m-%d').date()
                except:
                    val_data = datetime.now().date()
            else:
                val_data = datetime.now().date()
            data_pag = st.date_input("Vencimento 1ª Parcela", value=val_data, format="DD/MM/YYYY")
        
        ob = st.text_area("Objeto (Descrição)", value=safe_get(dd, 'proposta_objeto', ''), key="txt_objeto")
        
        cb1, cb2 = st.columns(2)
        
        # Botão SALVAR e GERAR
        if cb1.button("💾 Salvar e Atualizar DOC", type="primary"):
            # 1. Salvar no Banco
            data_str = data_pag.strftime('%Y-%m-%d') if data_pag else None
            db.sql_run("UPDATE clientes SET proposta_valor=?, proposta_entrada=?, proposta_parcelas=?, proposta_pagamento=?, proposta_objeto=?, proposta_data_pagamento=? WHERE id=?", 
                       (vp, ve, np_parc, pg, ob, data_str, int(safe_get(dd, 'id'))))
            
            # 2. Gerar Documento Atualizado (COM CACHE)
            # Criar chave de cache baseada nos dados
            cache_key = f"proposta_{safe_get(dd, 'id')}_{vp}_{ve}_{np_parc}_{pg}_{ob}"
            
            # Verificar se já existe no session_state e se é da mesma versão
            if st.session_state.get('doc_proposta_cache_key') != cache_key:
                doc_data = {
                    'nome': safe_get(dd, 'nome'), 
                    'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                    'telefone': safe_get(dd, 'telefone'),
                    'proposta_valor': vp, 
                    'proposta_entrada': ve, 
                    'proposta_parcelas': np_parc, 
                    'proposta_objeto': ob, 
                    'proposta_pagamento': pg,
                    'proposta_data_pagamento': data_str
                }
                doc_bytes = ut.criar_doc("Proposta", doc_data)
                st.session_state['doc_proposta_bytes'] = doc_bytes
                st.session_state['doc_proposta_nome'] = f"Prop_{safe_get(dd, 'nome')}.docx"
                st.session_state['doc_proposta_cache_key'] = cache_key
            
            st.success("Proposta salva e documento atualizado!")
            st.rerun()
            
        with cb2:
            # Botão de Download (Pega do Session State ou Gera do DB)
            # Botão de Download (Pega do Session State ou Gera do DB)
            doc_download = st.session_state.get('doc_proposta_bytes')
            nome_download = st.session_state.get('doc_proposta_nome', f"Prop_{safe_get(dd, 'nome')}.docx")
            
            if not doc_download:
                # Se não tem no state, gera com o que tem no banco (dd)
                doc_data_db = {
                    'nome': safe_get(dd, 'nome'), 
                    'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                    'telefone': safe_get(dd, 'telefone'),
                    'proposta_valor': ut.safe_float(safe_get(dd, 'proposta_valor')), 
                    'proposta_entrada': ut.safe_float(safe_get(dd, 'proposta_entrada')), 
                    'proposta_parcelas': ut.safe_int(safe_get(dd, 'proposta_parcelas')), 
                    'proposta_objeto': safe_get(dd, 'proposta_objeto', ''), 
                    'proposta_pagamento': safe_get(dd, 'proposta_pagamento')
                }
                doc_download = ut.criar_doc("Proposta", doc_data_db)
                st.caption("⚠️ Baixa a versão salva anteriormente.")
            
            st.download_button(
                "📄 Baixar DOC Proposta", 
                doc_download, 
                nome_download, 
                type="secondary"
            )

    # MODO DOCUMENTOS JURÍDICOS
    with st.expander("📄 Documentos Jurídicos", expanded=False):
        st.markdown("**Gerar documentos padrão para o cliente**")
        st.caption("Os documentos são gerados automaticamente com os dados cadastrados do cliente")
        
        col_doc1, col_doc2 = st.columns(2)
        
        # === PROCURAÇÃO ===
        with col_doc1:
            st.markdown("#### ⚖️ Procuração Ad Judicia")
            st.caption("Procuração judicial completa")
            
            # Opção de poderes especiais
            poderes_especiais = st.checkbox(
                "Incluir poderes especiais",
                value=True,
                key=f"procuracao_poderes_{safe_get(dd, 'id')}",
                help="Receber citação, transigir, desistir, etc."
            )
            
            col_p1, col_p2 = st.columns(2)
            
            # Botão GERAR
            if col_p1.button("📝 Gerar", key=f"btn_proc_{safe_get(dd, 'id')}", type="secondary", use_container_width=True):
                try:
                    doc_data = {
                        'nome': safe_get(dd, 'nome'),
                        'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                        'endereco': safe_get(dd, 'endereco', ''),
                        'numero_casa': safe_get(dd, 'numero_casa', ''),
                        'complemento': safe_get(dd, 'complemento', ''),
                        'bairro': safe_get(dd, 'bairro', ''),
                        'cidade': safe_get(dd, 'cidade', ''),
                        'estado': safe_get(dd, 'estado', ''),
                        'cep': safe_get(dd, 'cep', ''),
                        'estado_civil': safe_get(dd, 'estado_civil', ''),
                        'profissao': safe_get(dd, 'profissao', ''),
                        'proposta_objeto': safe_get(dd, 'proposta_objeto', 'Ação Judicial')
                    }
                    
                    opcoes = {'poderes_especiais': poderes_especiais}
                    
                    doc_bytes = ut.criar_doc("Procuracao", doc_data, opcoes=opcoes)
                    st.session_state['doc_procuracao_bytes'] = doc_bytes
                    st.session_state['doc_procuracao_nome'] = f"Procuracao_{safe_get(dd, 'nome').replace(' ', '_')}.docx"
                    
                    st.success("✅ Procuração gerada!")
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Erro ao gerar procuração: {e}", exc_info=True)
                    st.error(f"Erro ao gerar procuração: {e}")
            
            # Botão BAIXAR
            with col_p2:
                doc_procuracao = st.session_state.get('doc_procuracao_bytes')
                nome_procuracao = st.session_state.get('doc_procuracao_nome', f"Procuracao_{safe_get(dd, 'nome').replace(' ', '_')}.docx")
                
                if doc_procuracao:
                    st.download_button(
                        "📥 Baixar",
                        doc_procuracao,
                        nome_procuracao,
                        key=f"dl_proc_{safe_get(dd, 'id')}",
                        use_container_width=True
                    )
                else:
                    st.button("📥 Baixar", disabled=True, use_container_width=True, help="Gere o documento primeiro", key=f"dl_proc_disabled_{safe_get(dd, 'id')}")
        
        # === HIPOSSUFICIÊNCIA ===
        with col_doc2:
            st.markdown("#### 💰 Declaração de Hipossuficiência")
            st.caption("Declaração para gratuidade da justiça")
            
            # Renda mensal (opcional)
            renda_mensal = st.number_input(
                "Renda Mensal (R$) - Opcional",
                min_value=0.0,
                value=0.0,
                step=100.0,
                key=f"hipo_renda_{safe_get(dd, 'id')}",
                help="Deixe 0 se não quiser incluir"
            )
            
            col_h1, col_h2 = st.columns(2)
            
            # Botão GERAR
            if col_h1.button("📝 Gerar", key=f"btn_hipo_{safe_get(dd, 'id')}", type="secondary", use_container_width=True):
                try:
                    doc_data = {
                        'nome': safe_get(dd, 'nome'),
                        'nacionalidade': safe_get(dd, 'nacionalidade', 'brasileira'),
                        'estado_civil': safe_get(dd, 'estado_civil', ''),
                        'profissao': safe_get(dd, 'profissao', ''),
                        'rg': safe_get(dd, 'rg', ''),
                        'orgao_emissor': safe_get(dd, 'orgao_emissor', ''),
                        'cpf_cnpj': safe_get(dd, 'cpf_cnpj'),
                        'endereco': safe_get(dd, 'endereco', ''),
                        'numero_casa': safe_get(dd, 'numero_casa', ''),
                        'bairro': safe_get(dd, 'bairro', ''),
                        'cidade': safe_get(dd, 'cidade', ''),
                        'estado': safe_get(dd, 'estado', ''),
                        'cep': safe_get(dd, 'cep', ''),
                    }
                    
                    if renda_mensal > 0:
                        doc_data['renda_mensal'] = renda_mensal
                    
                    doc_bytes = ut.criar_doc("Hipossuficiencia", doc_data)
                    st.session_state['doc_hipo_bytes'] = doc_bytes
                    st.session_state['doc_hipo_nome'] = f"Hipossuficiencia_{safe_get(dd, 'nome').replace(' ', '_')}.docx"
                    
                    st.success("✅ Declaração gerada!")
                    st.rerun()
                    
                except Exception as e:
                    logger.error(f"Erro ao gerar hipossuficiência: {e}", exc_info=True)
                    st.error(f"Erro ao gerar hipossuficiência: {e}")
            
            # Botão BAIXAR
            with col_h2:
                doc_hipo = st.session_state.get('doc_hipo_bytes')
                nome_hipo = st.session_state.get('doc_hipo_nome', f"Hipossuficiencia_{safe_get(dd, 'nome').replace(' ', '_')}.docx")
                
                if doc_hipo:
                    st.download_button(
                        "📥 Baixar",
                        doc_hipo,
                        nome_hipo,
                        key=f"dl_hipo_{safe_get(dd, 'id')}",
                        use_container_width=True
                    )
                else:
                    st.button("📥 Baixar", disabled=True, use_container_width=True, help="Gere o documento primeiro", key=f"dl_hipo_disabled_{safe_get(dd, 'id')}")
    
    # MODO DOCUMENTAÇÃO (Visível para ATIVO e EM NEGOCIAÇÃO)
    if safe_get(dd, 'status_cliente') in ['ATIVO', 'EM NEGOCIAÇÃO']:
        if st.button("✅ Converter em Processo", help="Cria um processo automaticamente com base na proposta"):
             st.session_state.pre_fill_client = safe_get(dd, 'nome')
             st.session_state.next_nav = "Processos"
             st.success("Redirecionando para criação de processo...")
             st.rerun()
             
    # Botão de Exclusão com Segurança
    delete_key = f"del_cli_{safe_get(dd, 'id')}"
    
    if st.button("🗑️ Excluir Cliente", type="primary", use_container_width=True):
        st.session_state[delete_key] = True
        st.rerun()
        
    if st.session_state.get(delete_key, False):
        st.markdown("---")
        with st.container(border=True):
            st.warning("⚠️ **Confirmação de Exclusão**")
            
            # Verificar vínculos
            processos_vinculados = db.sql_get_query("SELECT COUNT(*) as total FROM processos WHERE id_cliente = ?", (safe_get(dd, 'id'),))
            financeiro_vinculado = db.sql_get_query("SELECT COUNT(*) as total FROM financeiro WHERE id_cliente = ?", (safe_get(dd, 'id'),))
            
            total_processos = processos_vinculados.iloc[0]['total'] if not processos_vinculados.empty else 0
            total_financeiro = financeiro_vinculado.iloc[0]['total'] if not financeiro_vinculado.empty else 0
            
            if total_processos > 0 or total_financeiro > 0:
                st.error(f"❌ Não é possível excluir: {total_processos} processos e {total_financeiro} lançamentos vinculados.")
                st.info("Transfira ou apague os vínculos antes de excluir o cliente.")
                if st.button("Ok, entendi"):
                    st.session_state[delete_key] = False
                    st.rerun()
            else:
                st.success("✅ Sem vínculos ativos. Seguro para excluir.")
                nome_confirmacao = st.text_input("Digite o nome do cliente para confirmar:", key=f"inp_del_{safe_get(dd, 'id')}")
                
                c_del1, c_del2 = st.columns(2)
                if c_del1.button("✅ CONFIRMAR", type="primary"):
                    if nome_confirmacao.strip().lower() == safe_get(dd, 'nome').strip().lower():
                        db.sql_run("DELETE FROM clientes WHERE id=?", (int(safe_get(dd, 'id')),))
                        st.success("Cliente excluído com sucesso!")
                        st.balloons()
                        time.sleep(1)
                        st.session_state.pop("nav_selection", None) # Reset nav se necessário
                        st.rerun()
                    else:
                        st.error("Nome incorreto.")
                
                if c_del2.button("❌ Cancelar"):
                    st.session_state[delete_key] = False
                    st.rerun()

# --- FUNÇÕES AUXILIARES PARA TIMELINE E CARD ---
def registrar_evento_timeline(cliente_id, tipo, titulo, descricao="", icone=""):
    """Registra evento na timeline do cliente"""
    try:
        db.sql_run("""
            INSERT INTO cliente_timeline (cliente_id, tipo_evento, titulo, descricao, icone)
            VALUES (?, ?, ?, ?, ?)
        """, (cliente_id, tipo, titulo, descricao, icone))
    except Exception as e:
        logger.error(f"Erro ao registrar evento timeline para cliente {cliente_id}: {e}")
def get_cliente_timeline(cliente_id):
    """Busca eventos do cliente ordenados por data"""
    try:
        return db.sql_get_query("""
            SELECT * FROM cliente_timeline 
            WHERE cliente_id = ? 
            ORDER BY data_evento DESC
            LIMIT 50
        """, (cliente_id,))
    except Exception as e:
        logger.debug(f"Erro ao buscar timeline do cliente: {e}")
        return pd.DataFrame()
def render_timeline_avancada(cliente_id):
    """Renderiza timeline moderna do cliente"""
    eventos = get_cliente_timeline(cliente_id)
    
    if eventos.empty:
        st.info("📝 Nenhum evento registrado ainda")
        return
    
    html = '<div class="cliente-timeline">'
    
    for _, ev in eventos.iterrows():
        try:
            data_obj = datetime.fromisoformat(ev['data_evento'])
            data_fmt = data_obj.strftime('%d/%m/%Y %H:%M')
        except:
            data_fmt = str(ev['data_evento'])[:16]
        
        tipo_evento = ev.get('tipo_evento', 'status')
        dot_class = f"timeline-dot {tipo_evento}"
        icone = ev.get('icone', '●')
        
        html += f"""
        <div class="timeline-event">
            <div class="{dot_class}">{icone}</div>
            <div class="timeline-date">{data_fmt}</div>
            <div class="timeline-title">{ev['titulo']}</div>"""
        
        if ev.get('descricao'):
            html += f'<div class="timeline-desc">{ev["descricao"]}</div>'
        
        html += '</div>'
    
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)
def render_cliente_card(dd):
    """Card de resumo visual do cliente"""
    try:
        processos = db.sql_get_query(
            "SELECT COUNT(*) as total FROM processos WHERE cliente_nome = ?", 
            (safe_get(dd, 'nome'),)
        )
        processos_count = processos.iloc[0]['total'] if not processos.empty else 0
    except Exception as e:
        logger.error(f"Erro ao buscar processos do cliente: {e}")
        processos_count = 0
    
    try:
        financeiro = db.sql_get_query("""
            SELECT SUM(valor) as total 
            FROM financeiro 
            WHERE cliente = ? AND status = 'pendente'
        """, (safe_get(dd, 'nome'),))
        pendente_total = financeiro.iloc[0]['total'] if not financeiro.empty and financeiro.iloc[0]['total'] else 0
    except Exception as e:
        logger.error(f"Erro ao buscar financeiro pendente do cliente: {e}")
        pendente_total = 0
    
    # NOVA FUNCIONALIDADE: Calcular última interação (OTIMIZADO)
    ultima_interacao = None
    dias_sem_contato = None
    fonte_interacao = ""
    
    cliente_id = safe_get(dd, 'id')
    cliente_nome = safe_get(dd, 'nome')
    
    # OTIMIZAÇÃO: Consolidar 4 queries em uma só com UNION
    try:
        query_consolidada = """
            SELECT MAX(data_interacao) as ultima, fonte FROM (
                SELECT MAX(data_evento) as data_interacao, 'timeline' as fonte 
                FROM cliente_timeline WHERE cliente_id = ?
                UNION ALL
                SELECT MAX(data) as data_interacao, 'financeiro' as fonte 
                FROM financeiro WHERE id_cliente = ?
                UNION ALL
                SELECT MAX(a.data_evento) as data_interacao, 'agenda' as fonte 
                FROM agenda a 
                JOIN processos p ON a.id_processo = p.id 
                WHERE p.cliente_nome = ?
            ) AS todas_interacoes
            WHERE data_interacao IS NOT NULL
            GROUP BY fonte
            ORDER BY data_interacao DESC
            LIMIT 1
        """
        
        resultado = db.sql_get_query(query_consolidada, (cliente_id, cliente_id, cliente_nome))
        
        if not resultado.empty and resultado.iloc[0]['ultima']:
            data_str = resultado.iloc[0]['ultima']
            fonte_interacao = resultado.iloc[0]['fonte']
            
            # Tentar parseor data (pode ser ISO ou formato YYYY-MM-DD)
            try:
                if 'T' in str(data_str):  # ISO format
                    ultima_interacao = datetime.fromisoformat(data_str)
                else:  # YYYY-MM-DD
                    ultima_interacao = datetime.strptime(data_str, '%Y-%m-%d')
            except Exception as e:
                logger.debug(f"Erro ao parsear data de interação '{data_str}': {e}")
                
    except Exception as e:
        logger.debug(f"Erro ao buscar última interação: {e}")
    
    # 4. Usar data de cadastro como fallback
    if not ultima_interacao:
        try:
            data_cad = safe_get(dd, 'data_cadastro')
            if data_cad:
                ultima_interacao = datetime.strptime(data_cad, '%Y-%m-%d')
                fonte_interacao = "cadastro"
        except Exception as e:
            logger.debug(f"Erro ao usar data de cadastro como fallback: {e}")
            
    # 5. Verificar Links Públicos Ativos
    links_ativos_count = 0
    try:
        # Buscar IDs dos processos do cliente
        procs_cli = db.sql_get_query("SELECT id FROM processos WHERE cliente_nome = ?", (cliente_nome,))
        if not procs_cli.empty:
            for pid in procs_cli['id'].tolist():
                ts = tm.listar_tokens_processo(pid)
                links_ativos_count += sum(1 for t in ts if t.get('ativo'))
    except Exception as e:
        logger.debug(f"Erro ao verificar links públicos: {e}")
            
    # Calcular Badge de Interação
    interacao_badge = ""
    if ultima_interacao:
        dias_sem_contato = (datetime.now() - ultima_interacao).days
        
        if dias_sem_contato <= 7:
            interacao_badge = f'<span style="color: #28a745; font-weight: bold;">✅ Há {dias_sem_contato} dias</span>'
        elif dias_sem_contato <= DIAS_SEM_CONTATO_ALERTA_AMARELO:
            interacao_badge = f'<span style="color: #ffc107; font-weight: bold;">⚠️ Há {dias_sem_contato} dias</span>'
        elif dias_sem_contato <= DIAS_SEM_CONTATO_ALERTA_LARANJA:
            interacao_badge = f'<span style="color: #fd7e14; font-weight: bold;">🔶 Há {dias_sem_contato} dias</span>'
        else:
            interacao_badge = f'<span style="color: #dc3545; font-weight: bold;">🔴 Há {dias_sem_contato} dias!</span>'
    else:
        interacao_badge = '<span style="color: #6c757d;">❓ Sem registro</span>'

    # --- COR FIXA: AZUL PISCINA (Removido selectbox) ---
    classe_cor = 'azul'  # Fixo em Azul Piscina

    # Preparar Badges de forma segura
    str_interacao = str(interacao_badge) if interacao_badge else '<span style="color: #6c757d;">❓</span>'
    
    status_icon = "✅" if safe_get(dd, 'status_cliente') == "ATIVO" else "🔔" if safe_get(dd, 'status_cliente') == "EM NEGOCIAÇÃO" else "⏹️"
    
    # Gerar link do WhatsApp
    tel_raw = ut.limpar_numeros(str(safe_get(dd, 'telefone', '')))
    if tel_raw:
        link_wpp = f"https://wa.me/55{tel_raw}"
        tel_display = f'<a href="{link_wpp}" target="_blank" style="text-decoration: none; color: #0f172a; font-weight: 500;">📞 {safe_get(dd, "telefone")}</a>'
    else:
        tel_display = f'📞 {safe_get(dd, "telefone", "N/A")}'

    # Renderizar Card HTML Premium (Design ID Card / Cartão de Crédito)
    st.markdown(f"""
    <div class="cliente-card {classe_cor}">
        <h2 style="font-size: 1.5rem; color: #0f172a; margin-bottom: 0.5rem;">{status_icon} {safe_get(dd, 'nome')}</h2>
        <p style="font-size: 1rem; color: #334155;">{tel_display} &nbsp;|&nbsp; 📧 {safe_get(dd, 'email', 'N/A')}</p>
        <p style="font-size: 0.95rem; color: #475569;">📍 {safe_get(dd, 'cidade', 'N/A')}, {safe_get(dd, 'estado', 'N/A')}</p>
        <hr style="border-color: rgba(15, 23, 42, 0.15);">
        <div class="cliente-metrics">
            <div class="metric-item" style="font-size: 0.85rem;">📊 Processos: <b>{processos_count}</b></div>
            <div class="metric-item" style="font-size: 0.85rem;">💰 Pendente: <b>R$ {pendente_total:.2f}</b></div>
            <div class="metric-item" style="font-size: 0.85rem;">🕐 Interação: {interacao_badge}</div>
            <div class="metric-item" style="font-size: 0.85rem;">🔗 Links: <b>{links_ativos_count}</b></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Alerta visual se muito tempo sem contato
    if dias_sem_contato and dias_sem_contato > DIAS_SEM_CONTATO_ALERTA_AMARELO:
        st.warning(f"⏰ **Atenção:** Sem contato há {dias_sem_contato} dias. Considere entrar em contato com o cliente!")
    
    # --- LINKS PÚBLICOS ATIVOS DOS PROCESSOS DO CLIENTE ---
    try:
        # Buscar processos do cliente
        processos_cliente = db.sql_get_query("SELECT id, numero, acao FROM processos WHERE cliente_nome = ?", (cliente_nome,))
        
        if not processos_cliente.empty:
            links_ativos = []
            for _, proc in processos_cliente.iterrows():
                tokens = tm.listar_tokens_processo(proc['id'])
                for t in tokens:
                    if t.get('ativo'):
                        links_ativos.append({
                            'processo': proc.get('numero') or proc.get('acao', ''),
                            'processo_id': proc['id'],
                            'token': t['token'],
                            'expira': t['data_expiracao'],
                            'acessos': t['acessos']
                        })
            
            if links_ativos:
                st.markdown("#### 🔗 Links Públicos Ativos")
                
                # Layout de cards em grid
                cols_count = LINKS_GRID_COLUMNS
                rows = math.ceil(len(links_ativos) / cols_count)
                
                for r in range(rows):
                    cols = st.columns(cols_count)
                    for c in range(cols_count):
                        idx = r * cols_count + c
                        if idx < len(links_ativos):
                            link = links_ativos[idx]
                            with cols[c]:
                                # Card Container
                                with st.container(border=True):
                                    # Info
                                    try:
                                        data_exp = link['expira'][:10]
                                        data_fmt = datetime.strptime(data_exp, '%Y-%m-%d').strftime('%d/%m/%Y')
                                    except:
                                        data_fmt = str(link['expira'])[:10]
                                    
                                    # CSS Class Injector for this specific card? Not easy in Streamlit loops.
                                    # We rely on the global CSS for 'stVerticalBlock' or just standard styling
                                    
                                    st.markdown(f"**📂 {link['processo']}**")
                                    st.caption(f"📅 Validade: {data_fmt}")
                                    st.caption(f"👀 Acessos: {link['acessos']}")
                                    
                                    # Link Copy
                                    url_base = db.get_config('url_sistema', 'http://localhost:8501')
                                    final_link = f"{url_base}/?token={link['token']}"
                                    st.code(final_link, language="text")
                                    
                                    # Actions Row
                                    ac1, ac2 = st.columns(2)
                                    
                                    # WhatsApp
                                    msg = f"Olá! Segue o link para acompanhar seu processo:\n\n📋 {link['processo']}\n\n🔗 {final_link}"
                                    msg_enc = msg.replace(" ", "%20").replace("\n", "%0A")
                                    wa_url = f"https://wa.me/?text={msg_enc}"
                                    if tel_raw:
                                        wa_url = f"https://wa.me/55{tel_raw}?text={msg_enc}"
                                        
                                    ac1.link_button("📱 Enviar", wa_url, use_container_width=True)
                                    
                                    # Delete
                                    if ac2.button("🗑️", key=f"del_lnk_n_{link['token']}", use_container_width=True):
                                        tm.excluir_token_publico(link['token'])
                                        st.toast("Link excluído!")
                                        time.sleep(0.5)
                                        st.rerun()

    except Exception as e:
        st.error(f"Erro ao carregar links: {e}")

# --- CALLBACKS ---

def salvar_cliente_callback():
    nome = st.session_state.cad_nome
    cpf_cnpj = ut.limpar_numeros(st.session_state.cad_cpf_cnpj)
    tipo_pessoa = st.session_state.cad_tipo_pessoa
    
    if not nome or not cpf_cnpj: 
        st.toast("Nome e Documento obrigatórios!", icon="⚠️")
        return
    
    if db.cpf_existe(cpf_cnpj): 
        st.toast("Documento já cadastrado!", icon="❌")
        return
    
    # Validação LGPD (Fase 2)
    if not st.session_state.get('cad_lgpd', False):
        st.toast("⚠️ Consentimento LGPD obrigatório!", icon="🔐")
        return

    # Validação de E-mail com regex robusto
    email = st.session_state.cad_email
    if email and not re.fullmatch(EMAIL_REGEX, email):
        st.toast("❌ E-mail inválido! Use o formato: usuario@dominio.com", icon="❌")
        return
    
    # Validação de CPF ou CNPJ
    valido = False
    if tipo_pessoa == "Física":
        valido = ut.validar_cpf_matematico(cpf_cnpj)
    else:
        valido = ut.validar_cnpj(cpf_cnpj)
        
    if not valido: 
        st.toast(f"{tipo_pessoa} Inválido!", icon="❌")
        return

    # Proteção contra clique duplo - CORRIGIDO: atomic check-and-set
    if 'salvando_cliente' not in st.session_state:
        st.session_state['salvando_cliente'] = False
    
    if st.session_state['salvando_cliente']:
        st.toast("⚠️ Salvamento em andamento, aguarde...", icon="⏳")
        return
    
    # Set atômico
    st.session_state['salvando_cliente'] = True

    try:
        # Preparar data de nascimento
        data_nasc = None
        if st.session_state.get('cad_data_nascimento'):
            data_nasc = st.session_state.cad_data_nascimento.strftime("%Y-%m-%d")
        
        # Criptografar CPF/CNPJ antes de salvar (LGPD)
        cpf_cnpj_encrypted = crypto.encrypt(cpf_cnpj)
        
        # --- CRIAR PASTA NO GOOGLE DRIVE AUTOMATICAMENTE ---
        drive_link = st.session_state.get('cad_drive', '')  # Link manual, se fornecido
        
        if not drive_link:  # Se não forneceu link manual, criar pasta automaticamente
            try:
                service = gd.autenticar()
                if service:
                    # CORRIGIDO: Criar hierarquia Clientes/NomeCliente
                    # 1. Primeiro encontrar ou criar pasta "Clientes"
                    pasta_clientes = gd.find_folder(service, "Clientes", gd.PASTA_ALVO_ID)
                    if not pasta_clientes:
                        pasta_clientes = gd.create_folder(service, "Clientes", gd.PASTA_ALVO_ID)
                    
                    if pasta_clientes:
                        # 2. Criar pasta do cliente DENTRO de "Clientes"
                        folder_id = gd.create_folder(service, nome, pasta_clientes)
                        if folder_id:
                            drive_link = f"https://drive.google.com/drive/folders/{folder_id}"
                            st.toast(f"✅ Pasta criada: Clientes/{nome}", icon="📂")
                        else:
                            st.warning("⚠️ Não foi possível criar pasta do cliente")
                    else:
                        st.warning("⚠️ Não foi possível criar pasta Clientes")
                else:
                    st.warning("⚠️ Google Drive não autenticado")
            except Exception as e:
                logger.error(f"Erro ao criar pasta no Drive: {e}")
                st.warning(f"⚠️ Erro no Drive: {e}")
        
        db.sql_run('''INSERT INTO clientes (
            nome, tipo_pessoa, cpf_cnpj, email, telefone, telefone_fixo, profissao, estado_civil, 
            cep, endereco, numero_casa, complemento, bairro, cidade, estado, obs, 
            status_cliente, link_drive, data_cadastro, rg, orgao_emissor, nacionalidade, data_nascimento,
            lgpd_consentimento, lgpd_data_consentimento
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''', 
        (
            nome, tipo_pessoa, cpf_cnpj_encrypted, st.session_state.cad_email, st.session_state.cad_tel, 
            st.session_state.cad_fixo, st.session_state.cad_prof, st.session_state.cad_ec, 
            st.session_state.cad_cep, st.session_state.cad_rua, st.session_state.cad_num, 
            st.session_state.cad_comp, st.session_state.cad_bairro, st.session_state.cad_cid, 
            st.session_state.cad_uf, st.session_state.cad_obs, st.session_state.cad_stt, 
            drive_link, datetime.now().strftime("%Y-%m-%d"),
            st.session_state.get('cad_rg', ''), st.session_state.get('cad_orgao_emissor', ''),
            st.session_state.get('cad_nacionalidade', ''), data_nasc,
            1, datetime.now().isoformat()  # LGPD: consentimento e data
        ))
        st.toast(f"Cliente {nome} Salvo!", icon="✅")
        
        # --- ENVIAR E-MAIL DE BOAS-VINDAS ---
        if email:  # Se o cliente informou e-mail
            try:
                telefone_escritorio = db.get_config('telefone_escritorio') or "(21) 99999-9999"
                corpo_email = email_templates.template_boas_vindas(nome, telefone_escritorio)
                sucesso, erro = utils_email.enviar_email(
                    email, 
                    "Bem-vindo(a) ao escritório Lopes & Ribeiro!", 
                    corpo_email
                )
                if sucesso:
                    st.toast("📧 E-mail de boas-vindas enviado!", icon="✅")
                else:
                    logger.warning(f"E-mail não enviado para {email}: {erro}")
                    st.toast(f"⚠️ E-mail não enviado: {erro}", icon="⚠️")
            except Exception as e_mail:
                # Não impedir o cadastro por erro de e-mail
                logger.error(f"Falha ao enviar e-mail de boas-vindas: {e_mail}")
                st.toast(f"⚠️ Falha ao enviar e-mail: {e_mail}", icon="⚠️")
        
        limpar_campos_cadastro()
        
    except Exception as e:
        logger.error(f"Erro ao salvar cliente: {e}")
        st.toast(f"Erro: {e}", icon="❌")
    finally:
        # CORRIGIDO: Garantir que flag sempre seja resetada
        st.session_state['salvando_cliente'] = False

def limpar_campos_cadastro():
    # CORRIGIDO: Incluir campo LGPD na limpeza
    campos = [
        'cad_nome', 'cad_cpf_cnpj', 'cad_email', 'cad_tel', 'cad_fixo', 'cad_prof', 'cad_ec', 
        'cad_cep', 'cad_rua', 'cad_num', 'cad_comp', 'cad_bairro', 'cad_cid', 'cad_uf', 
        'cad_obs', 'cad_drive', 'cad_rg', 'cad_orgao_emissor', 'cad_nacionalidade', 'cad_lgpd'
    ]
    for campo in campos:
        if campo in st.session_state:
            if campo == 'cad_lgpd':
                st.session_state[campo] = False  # Checkbox volta para desmarcado
            else:
                st.session_state[campo] = ""
    # Limpar campo de data também
    if 'cad_data_nascimento' in st.session_state:
        del st.session_state['cad_data_nascimento']
