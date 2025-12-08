"""
Interface de busca DataJud para integração no módulo Processos

Este módulo contém a UI completa para buscar processos no DataJud
"""

import streamlit as st
import database as db
import pandas as pd
import datajud

def render_busca_datajud():
    """
    Renderiza interface de busca no DataJud
    
    Returns:
        dict ou None: Dados do processo importado ou None
    """
    
    st.markdown("#### 🔍 Buscar Processo no DataJud (CNJ)")
    
    with st.expander("💡 Importar dados automaticamente", expanded=True):
        col_num, col_btn = st.columns([3, 1])
        
        numero_cnj = col_num.text_input(
            "Número do Processo (CNJ)",
            placeholder="0000000-00.0000.0.00.0000",
            help="Digite o número completo do processo (20 dígitos)",
            key="datajud_numero"
        )
        
        col_btn.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
        buscar_btn = col_btn.button("🔍 Buscar", type="primary", use_container_width=True)
        
        if buscar_btn:
            if not numero_cnj or numero_cnj.strip() == "":
                st.error("❌ Digite o número do processo")
            else:
                # Validar formato
                valido, erro_validacao = datajud.validar_numero_cnj(numero_cnj)
                
                if not valido:
                    st.error(f"❌ {erro_validacao}")
                else:
                    # Buscar token
                    token = db.get_config('datajud_token', '')
                    
                    if not token:
                        st.error("🔑 Token DataJud não configurado")
                        st.info("Configure o token em: **Administração** → **Configurações** → **Integração DataJud**")
                        
                        if st.button("➡️ Ir para Administração"):
                            st.session_state.next_nav = "Administração"
                            st.rerun()
                    else:
                        # Identificar tribunal
                        tribunal, _ = datajud.identificar_tribunal(numero_cnj)
                        
                        if tribunal:
                            st.info(f"🏛️ Tribunal identificado: **{tribunal}**")
                        
                        # Buscar processo
                        with st.spinner("🔍 Consultando DataJud..."):
                            dados_processo, erro = datajud.consultar_processo(numero_cnj, token)
                        
                        # --- DEBUG: Ver JSON Bruto ---
                        with st.expander("🛠️ Dados Técnicos (Debug JSON)", expanded=False):
                            if dados_processo:
                                st.json(dados_processo)
                            elif erro:
                                st.error(erro)
                        # -----------------------------
                        
                        if erro:
                            st.error(erro)
                            
                            # Se for erro de token, mostrar link para admin
                            if "Token" in erro or "expirado" in erro:
                                if st.button("🔑 Atualizar Token"):
                                    st.session_state.next_nav = "Administração"
                                    st.rerun()
                        else:
                            # Sucesso! Parsear dados
                            dados_limpos = datajud.parsear_dados(dados_processo)
                            
                            st.success("✅ Processo encontrado!")
                            
                            # Mostrar resumo
                            with st.container(border=True):
                                st.markdown(f"**📋 {dados_limpos['numero']}**")
                                st.caption(f"**Classe:** {dados_limpos['classe']}")
                                st.caption(f"**Órgão:** {dados_limpos['orgao_julgador']}")
                                
                                if dados_limpos['data_ajuizamento']:
                                    data_fmt = datajud.formatar_data_br(dados_limpos['data_ajuizamento'])
                                    st.caption(f"**Ajuizado em:** {data_fmt}")
                            
                            # Selecionar qual parte é o cliente
                            st.markdown("---")
                            st.markdown("**👥 Quem é seu cliente neste processo?**")
                            
                            partes = dados_limpos['partes']
                            
                            manual_client = False
                            parte_selecionada = None
                            
                            # === ESTRATÉGIA MULTI-CAMADA PARA ENCONTRAR PARTES ===
                            
                            # Debug: Mostrar quantos movimentos temos
                            movimentos_disponiveis = dados_limpos.get('movimentos', [])
                            numero_cnj = dados_limpos.get('numero', '')
                            
                            # TENTATIVA 0: Buscar no cache local (partes já digitadas anteriormente)
                            if not partes and numero_cnj:
                                partes_cache = db.buscar_partes_cache(numero_cnj)
                                if partes_cache:
                                    partes = partes_cache
                                    st.success(f"💾 {len(partes)} parte(s) encontrada(s) no cache!")
                            
                            with st.expander("🔍 Debug: Dados disponíveis", expanded=False):
                                st.write(f"Partes Cache: {len(db.buscar_partes_cache(numero_cnj)) if numero_cnj else 0}")
                                st.write(f"Partes API: {len(partes)}")
                                st.write(f"Movimentos: {len(movimentos_disponiveis)}")
                                if movimentos_disponiveis:
                                    st.write("Primeiros movimentos:")
                                    for m in movimentos_disponiveis[:3]:
                                        st.caption(f"- {m.get('descricao', 'N/A')[:100]}")
                            
                            # TENTATIVA 1: Partes já vieram da API parseada
                            if partes:
                                st.success(f"✅ {len(partes)} parte(s) encontrada(s)!")
                            
                            # TENTATIVA 2: Buscar partes diretamente no JSON bruto (dados_processo)
                            if not partes and dados_processo:
                                # Alguns tribunais colocam em 'polo' (array) ao invés de 'polos'
                                polos_raw = dados_processo.get('polos', dados_processo.get('polo', []))
                                if polos_raw:
                                    st.info(f"🔎 Encontrados {len(polos_raw)} polos no JSON bruto")
                                    for polo in polos_raw:
                                        tipo_polo = polo.get('polo', 'INDEFINIDO')
                                        if tipo_polo == 'AT': tipo_polo = 'AUTOR'
                                        elif tipo_polo == 'PA': tipo_polo = 'REU'
                                        
                                        for parte in polo.get('partes', polo.get('parte', [])):
                                            pessoa = parte.get('pessoa', parte)
                                            nome = pessoa.get('nome', parte.get('nome', ''))
                                            if nome:
                                                partes.append({
                                                    'nome': nome,
                                                    'tipo': tipo_polo,
                                                    'cpf_cnpj': '',
                                                    'tipo_pessoa': 'Física'
                                                })
                            
                            # NOTA: Tentativa TJRJ removida (URL antiga descontinuada)
                            
                            # TENTATIVA 3: Extrair via IA analisando TODO o texto disponível
                            if not partes:
                                import ai_gemini as ai
                                
                                # Coletar TODOS os textos disponíveis para análise
                                textos_para_ia = []
                                
                                # Adicionar movimentos
                                for m in movimentos_disponiveis:
                                    desc = m.get('descricao', '')
                                    compl = m.get('complemento', '')
                                    if desc:
                                        textos_para_ia.append(desc + (' ' + compl if compl else ''))
                                
                                # Se não houver movimentos, usar todos os campos de texto do JSON
                                if not textos_para_ia and dados_processo:
                                    # Extrair qualquer texto do JSON bruto
                                    def extrair_textos(obj, textos):
                                        if isinstance(obj, dict):
                                            for v in obj.values():
                                                extrair_textos(v, textos)
                                        elif isinstance(obj, list):
                                            for item in obj:
                                                extrair_textos(item, textos)
                                        elif isinstance(obj, str) and len(obj) > 10:
                                            textos.append(obj)
                                    extrair_textos(dados_processo, textos_para_ia)
                                
                                if textos_para_ia:
                                    with st.spinner("🤖 IA analisando dados para identificar partes..."):
                                        resultado_ia = ai.extrair_partes_processo(
                                            textos_para_ia[:20],  # Limitar a 20 textos
                                            dados_limpos.get('classe', ''),
                                            dados_limpos.get('orgao_julgador', '')
                                        )
                                        
                                        if resultado_ia.get('partes'):
                                            partes = resultado_ia['partes']
                                            st.info(f"🤖 IA identificou {len(partes)} parte(s)")
                                            if resultado_ia.get('observacao'):
                                                st.caption(f"Obs: {resultado_ia['observacao']}")
                                        else:
                                            st.warning(f"IA não conseguiu identificar partes. {resultado_ia.get('observacao', '')}")
                                else:
                                    st.warning("Nenhum texto disponível para análise de IA")
                            
                            # FALLBACK FINAL: Input manual com UX melhorada
                            if not partes:
                                with st.container(border=True):
                                    st.markdown("### ✍️ Cadastro Manual das Partes")
                                    st.caption("A API DataJud não retorna nomes das partes (LGPD). Digite abaixo:")
                                    
                                    col_cliente, col_contra = st.columns(2)
                                    
                                    with col_cliente:
                                        # Buscar clientes ativos do sistema
                                        clientes_df = db.sql_get_query(
                                            "SELECT id, nome, cpf_cnpj, tipo_pessoa FROM clientes WHERE status_cliente = 'ATIVO' ORDER BY nome ASC"
                                        )
                                        
                                        # Preparar opções do dropdown
                                        opcoes_clientes = ["📝 Digitar manualmente..."]
                                        mapa_clientes = {0: None}  # Índice 0 = manual
                                        
                                        if not clientes_df.empty:
                                            for idx, row in clientes_df.iterrows():
                                                doc = row['cpf_cnpj'] if pd.notna(row['cpf_cnpj']) and row['cpf_cnpj'] else ""
                                                tipo_ico = "🏢" if row.get('tipo_pessoa') == 'Jurídica' else "👤"
                                                label = f"{tipo_ico} {row['nome']}"
                                                if doc:
                                                    label += f" ({doc[:14]}{'...' if len(doc) > 14 else ''})"
                                                opcoes_clientes.append(label)
                                                mapa_clientes[len(opcoes_clientes) - 1] = {
                                                    'id': row['id'],
                                                    'nome': row['nome'],
                                                    'cpf_cnpj': doc,
                                                    'tipo_pessoa': row.get('tipo_pessoa', 'Física')
                                                }
                                        
                                        cliente_selecionado_idx = st.selectbox(
                                            "👤 Nome do seu Cliente",
                                            range(len(opcoes_clientes)),
                                            format_func=lambda x: opcoes_clientes[x],
                                            key="select_cliente_existente",
                                            help="Selecione um cliente já cadastrado ou escolha 'Digitar manualmente'"
                                        )
                                        
                                        # Determinar o nome do cliente baseado na seleção
                                        if cliente_selecionado_idx == 0:
                                            # Digitar manualmente
                                            manual_name = st.text_input("✏️ Digite o nome do cliente", key="manual_cliente_input")
                                            st.session_state['cliente_selecionado_dados'] = None
                                        else:
                                            # Cliente do dropdown
                                            cliente_dados = mapa_clientes.get(cliente_selecionado_idx)
                                            if cliente_dados:
                                                manual_name = cliente_dados['nome']
                                                st.success(f"✅ **{manual_name}**")
                                                st.session_state['cliente_selecionado_dados'] = cliente_dados
                                            else:
                                                manual_name = ""
                                        
                                        manual_tipo = st.radio("Posição no processo", ["AUTOR", "REU"], horizontal=True, key="manual_tipo")
                                    
                                    with col_contra:
                                        contra_name = st.text_input("👥 Parte Contrária (opcional)", key="manual_contra")
                                        if contra_name:
                                            st.caption(f"Será cadastrado como {'RÉU' if manual_tipo == 'AUTOR' else 'AUTOR'}")
                                
                                # Preparar parte selecionada (fora das colunas, mas dentro do container)
                                if manual_name:
                                    # Verificar se veio do dropdown (cliente já existe)
                                    cliente_do_dropdown = st.session_state.get('cliente_selecionado_dados')
                                    
                                    if cliente_do_dropdown and cliente_do_dropdown.get('nome') == manual_name:
                                        # Cliente selecionado do dropdown - usar dados completos
                                        parte_selecionada = {
                                            'nome': cliente_do_dropdown['nome'],
                                            'tipo': manual_tipo,
                                            'cpf_cnpj': cliente_do_dropdown.get('cpf_cnpj', ''),
                                            'tipo_pessoa': cliente_do_dropdown.get('tipo_pessoa', 'Física'),
                                            'id_cliente': cliente_do_dropdown.get('id')  # ID para vínculo direto
                                        }
                                    else:
                                        # Digitado manualmente
                                        parte_selecionada = {
                                            'nome': manual_name,
                                            'tipo': manual_tipo,
                                            'cpf_cnpj': '',
                                            'tipo_pessoa': 'Física'
                                        }
                                    
                                    manual_client = True
                                    
                                    # Guardar parte contrária para salvar depois
                                    if contra_name:
                                        st.session_state['parte_contraria_manual'] = {
                                            'nome': contra_name,
                                            'tipo': 'REU' if manual_tipo == 'AUTOR' else 'AUTOR',
                                            'cpf_cnpj': '',
                                            'tipo_pessoa': 'Física'
                                        }
                            else:
                                # Partes encontradas - mostrar opções para selecionar
                                opcoes_partes = []
                                for i, parte in enumerate(partes):
                                    tipo_icon = "⚖️" if parte['tipo'] == "AUTOR" else "🎯" if parte['tipo'] == "REU" else "📌"
                                    opcoes_partes.append(f"{tipo_icon} {parte['nome']} ({parte['tipo']})")
                                
                                parte_escolhida_idx = st.radio(
                                    "Selecione:",
                                    range(len(opcoes_partes)),
                                    format_func=lambda x: opcoes_partes[x],
                                    key="parte_selecionada"
                                )
                                
                                parte_selecionada = partes[parte_escolhida_idx]
                            
                            # Botão de importar - aparece sempre que parte_selecionada foi definida
                            st.markdown("---")
                            
                            if parte_selecionada:
                                if st.button("✅ Importar Dados", type="primary", use_container_width=True):
                                    # SALVAR PARTES NO CACHE para futuras consultas
                                    if numero_cnj:
                                        partes_para_cache = [
                                            {**parte_selecionada, 'is_cliente': True}
                                        ]
                                        # Adicionar parte contrária se existir
                                        if st.session_state.get('parte_contraria_manual'):
                                            partes_para_cache.append(st.session_state['parte_contraria_manual'])
                                        
                                        db.salvar_partes_cache(numero_cnj, partes_para_cache)

                                    # Verificar se cliente existe
                                    # Se veio do dropdown, já sabemos que existe
                                    cliente_tem_id = parte_selecionada.get('id_cliente')
                                    
                                    if cliente_tem_id:
                                        # Cliente selecionado do dropdown - já existe no sistema
                                        cliente_existe = True
                                    else:
                                        # Verificar no banco se foi digitado manualmente
                                        doc_cliente = parte_selecionada.get('cpf_cnpj', '')
                                        nome_cliente = parte_selecionada['nome']
                                        
                                        # Tenta buscar por CPF/CNPJ ou por nome
                                        if doc_cliente:
                                            df_cliente = db.sql_get_query(
                                                "SELECT id FROM clientes WHERE cpf_cnpj=?",
                                                (doc_cliente,)
                                            )
                                        else:
                                            # Buscar por nome exato (case insensitive)
                                            df_cliente = db.sql_get_query(
                                                "SELECT id FROM clientes WHERE LOWER(nome) = LOWER(?)",
                                                (nome_cliente,)
                                            )
                                        
                                        cliente_existe = not df_cliente.empty
                                        if cliente_existe:
                                            # Guardar o ID encontrado para uso posterior
                                            parte_selecionada['id_cliente'] = int(df_cliente.iloc[0]['id'])
                                    
                                    if not cliente_existe:
                                        st.warning(f"⚠️ **Cliente não cadastrado:** {parte_selecionada['nome']}")
                                        st.info("Cadastre este cliente primeiro no módulo **Clientes** e depois volte aqui.")
                                        
                                        if st.button("➡️ Ir para Clientes", key="btn_ir_clientes"):
                                            st.session_state.next_nav = "Clientes (CRM)"
                                            st.rerun()
                                            
                                        st.markdown("---")
                                        st.markdown(f"**Ou cadastre agora mesmo:**")
                                        if st.button(f"➕ Cadastrar '{parte_selecionada['nome']}' como Cliente", key="btn_cadastrar_cliente"):
                                            try:
                                                novo_cli = {
                                                    'nome': parte_selecionada['nome'],
                                                    'cpf_cnpj': parte_selecionada.get('cpf_cnpj', ''),
                                                    'status_cliente': 'ATIVO',
                                                    'tipo_pessoa': parte_selecionada.get('tipo_pessoa', 'Física')
                                                }
                                                db.crud_insert('clientes', novo_cli)
                                                st.success(f"✅ Cliente {parte_selecionada['nome']} cadastrado! Clique em Importar novamente.")
                                                st.rerun()
                                            except Exception as e:
                                                st.error(f"Erro ao cadastrar: {e}")
                                    else:
                                        # Cliente existe! Preencher formulário
                                        dados_importados = {
                                            'cliente': parte_selecionada['nome'],
                                            'id_cliente': parte_selecionada.get('id_cliente'),  # ID para vínculo direto
                                            'numero': dados_limpos['numero'],
                                            'fase': datajud.mapear_fase_processual(dados_limpos['classe']),
                                            'classe': dados_limpos['classe'],
                                            'orgao': dados_limpos['orgao_julgador'],
                                            'comarca': dados_limpos.get('comarca', ''),
                                            'movimentos': dados_limpos['movimentos'],
                                            'tribunal': tribunal if tribunal else dados_limpos.get('tribunal', 'Não identificado'),
                                            'valor_causa': dados_limpos.get('valor_causa', 0.0),
                                            'data_distribuicao': dados_limpos.get('data_ajuizamento', None),
                                            'partes_completas': partes,
                                            'parte_cliente_tipo': parte_selecionada['tipo']
                                        }

                                        st.session_state['datajud_importado'] = dados_importados
                                        st.success("✅ Dados importados com sucesso!")
                                        st.info("📝 Role para baixo para revisar os dados no formulário e salvar o processo.")
                                        st.balloons()
                                        
                                        return dados_importados
    
    return None

def processar_dados_importados(form_key_prefix="proc"):
    """
    Processa dados importados do DataJud e preenche formulário
    
    Args:
        form_key_prefix (str): Prefixo das chaves do formulário
        
    Returns:
        dict: Dados para preencher o formulário ou None
    """
    
    if 'datajud_importado' in st.session_state:
        dados = st.session_state['datajud_importado']
        
        # Exibir aviso de importação
        st.info(f"📥 **Dados importados do DataJud:** {dados['numero']}")
        
        # Retornar dados para o formulário
        return {
            'cliente': dados['cliente'],
            'acao': dados['numero'],
            'fase': dados['fase'],
            'valor_causa': dados.get('valor_causa', 0.0),
            'data_distribuicao': dados.get('data_distribuicao'),
            'parte_contraria_sugerida': _identificar_parte_contraria(dados)
        }
    
    return None

def _identificar_parte_contraria(dados):
    """Tenta identificar a parte contrária com base no cliente selecionado"""
    try:
        tipo_cliente = dados.get('parte_cliente_tipo') # AUTOR ou REU
        if not tipo_cliente: return None
        
        partes = dados.get('partes_completas', [])
        
        # Se cliente é AUTOR, busca o primeiro REU
        if tipo_cliente == 'AUTOR':
            for p in partes:
                if p['tipo'] == 'REU':
                    return p
                    
        # Se cliente é REU, busca o primeiro AUTOR
        elif tipo_cliente == 'REU':
             for p in partes:
                if p['tipo'] == 'AUTOR':
                    return p
                    
        return None
    except:
        return None

def importar_movimentacoes_datajud(processo_id):
    """
    Importa movimentações do processo do DataJud para a tabela andamentos
    
    Args:
        processo_id (int): ID do processo salvo
        
    Returns:
        int: Quantidade de movimentações importadas
    """
    
    if 'datajud_importado' not in st.session_state:
        return 0
    
    dados = st.session_state['datajud_importado']
    movimentos = dados.get('movimentos', [])
    
    if not movimentos:
        return 0
    
    import_count = 0
    
    try:
        for movimento in movimentos:
            # Validar campos
            data_mov = movimento.get('data', '')
            descricao = movimento.get('descricao', 'Movimentação sem descrição')
            complemento = movimento.get('complemento', '')
            
            # Formatar descrição completa
            desc_completa = descricao
            if complemento:
                desc_completa += f" - {complemento}"
            
            # Converter data
            data_formatada = data_mov[:10] if data_mov else None  # YYYY-MM-DD
            
            if data_formatada:
                # Inserir andamento
                db.sql_run(
                    "INSERT INTO andamentos (id_processo, data, descricao, responsavel) VALUES (?,?,?,?)",
                    (processo_id, data_formatada, desc_completa, "DataJud")
                )
                import_count += 1
                
    except Exception as e:
        st.error(f"Erro ao importar movimentações: {e}")
        return import_count
    
    # Limpar dados importados após uso
    if import_count > 0:
        del st.session_state['datajud_importado']
    
    return import_count
