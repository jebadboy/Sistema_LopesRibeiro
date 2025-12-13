import streamlit as st
import database as db
import pandas as pd
from datetime import datetime
import os
import tempfile
import io

# Importar ReportLab para geração de PDF
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_JUSTIFY, TA_CENTER
    PDF_DISPONIVEL = True
except ImportError:
    PDF_DISPONIVEL = False

# Importar google_drive para upload
try:
    import google_drive as gd
    DRIVE_DISPONIVEL = True
except ImportError:
    DRIVE_DISPONIVEL = False


def render():
    st.markdown("<h1 style='color: var(--text-main);'>📄 Automação de Documentos</h1>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs([
        "📝 Gerador de Documentos", 
        "⚙️ Gerenciar Modelos",
        "📚 Histórico Gerado",
        "📤 Upload para Drive"
    ])
    
    # --- ABA 1: GERADOR ---
    with tab1:
        render_gerador_documentos()
    
    # --- ABA 2: GERENCIAR MODELOS ---
    with tab2:
        render_gerenciar_modelos()
    
    # --- ABA 3: HISTÓRICO ---
    with tab3:
        render_historico_documentos()
    
    # --- ABA 4: UPLOAD PARA DRIVE ---
    with tab4:
        render_upload_drive()


def render_gerador_documentos():
    """Gerador de documentos a partir de templates."""
    st.markdown("### Gerar Novo Documento")
    
    col1, col2 = st.columns(2)
    with col1:
        # Selecionar Cliente
        df_clientes = db.sql_get("clientes", "nome")
        opcoes_clientes = df_clientes['nome'].tolist() if not df_clientes.empty else []
        cliente_selecionado = st.selectbox("Selecione o Cliente", [""] + opcoes_clientes)
        
    with col2:
        # Selecionar Modelo
        df_modelos = db.sql_get("modelos_documentos", "titulo")
        opcoes_modelos = df_modelos['titulo'].tolist() if not df_modelos.empty else []
        modelo_selecionado = st.selectbox("Selecione o Modelo", [""] + opcoes_modelos)
    
    if not cliente_selecionado or not modelo_selecionado:
        st.info("Selecione um cliente e um modelo para gerar o documento.")
        return
    
    # Buscar dados do cliente
    dados_cliente = df_clientes[df_clientes['nome'] == cliente_selecionado].iloc[0].to_dict()
    id_cliente = dados_cliente.get('id')
    
    # --- Mapeamento e Campos Compostos ---
    dados_cliente['cpf'] = dados_cliente.get('cpf_cnpj', '')
    dados_cliente['cnpj'] = dados_cliente.get('cpf_cnpj', '')
    dados_cliente['data_atual'] = datetime.now().strftime('%d/%m/%Y')
    dados_cliente['data_extenso'] = formatar_data_extenso(datetime.now())
    
    parts_endereco = [
        dados_cliente.get('endereco', ''),
        (f"nº {dados_cliente.get('numero_casa')}" if dados_cliente.get('numero_casa') else ''),
        dados_cliente.get('complemento', ''),
        dados_cliente.get('bairro', ''),
        (f"{dados_cliente.get('cidade', '')}-{dados_cliente.get('estado', '')}" if dados_cliente.get('cidade') else '')
    ]
    dados_cliente['endereco_completo'] = ", ".join([p for p in parts_endereco if p])
    
    id_modelo = df_modelos[df_modelos['titulo'] == modelo_selecionado].iloc[0]['id']
    modelo_categoria = df_modelos[df_modelos['titulo'] == modelo_selecionado].iloc[0].get('categoria', 'Documento')
    
    # Opções do documento
    st.markdown("#### ⚙️ Opções")
    col_opcoes = st.columns(2)
    with col_opcoes[0]:
        incluir_assinatura = st.checkbox(
            "✍️ Incluir campo para assinatura digital",
            value=False,
            help="Adiciona área de assinatura no final do PDF para uso com token OAB"
        )
    
    # Gerar Preview
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        gerar_preview = st.button("👁️ Gerar Preview", type="primary", use_container_width=True)
    
    with col_btn2:
        gerar_e_salvar = st.button("💾 Gerar e Salvar no Histórico", use_container_width=True)
    
    if gerar_preview or gerar_e_salvar:
        texto_gerado = db.gerar_documento_final(id_modelo, dados_cliente)
        
        st.markdown("---")
        st.markdown("### 👁️ Visualização")
        st.text_area("Conteúdo Gerado", value=texto_gerado, height=400, key="preview_doc")
        
        # Botões de ação
        col_actions = st.columns(3)
        
        with col_actions[0]:
            # Download como TXT
            st.download_button(
                "📥 Download TXT",
                data=texto_gerado,
                file_name=f"{modelo_selecionado}_{cliente_selecionado.replace(' ', '_')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        with col_actions[1]:
            # Download como PDF
            if PDF_DISPONIVEL:
                pdf_bytes = gerar_pdf(
                    texto=texto_gerado,
                    titulo=modelo_selecionado,
                    cliente=cliente_selecionado,
                    incluir_assinatura=incluir_assinatura
                )
                st.download_button(
                    "📥 Download PDF",
                    data=pdf_bytes,
                    file_name=f"{modelo_selecionado}_{cliente_selecionado.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            else:
                st.warning("⚠️ ReportLab não instalado")
        
        with col_actions[2]:
            # Copiar para área de transferência (instrução)
            st.info("💡 Selecione o texto acima e use Ctrl+C para copiar")
        
        # Salvar no histórico
        if gerar_e_salvar:
            salvar_documento_historico(
                id_cliente=id_cliente,
                cliente_nome=cliente_selecionado,
                modelo_nome=modelo_selecionado,
                categoria=modelo_categoria,
                conteudo=texto_gerado
            )
            st.success("✅ Documento salvo no histórico!")


def render_gerenciar_modelos():
    """Gerenciamento de modelos de documento."""
    st.markdown("### Meus Modelos")
    
    with st.expander("➕ Criar Novo Modelo", expanded=False):
        with st.form("novo_modelo"):
            titulo = st.text_input("Título do Modelo (ex: Procuração Geral)")
            categoria = st.selectbox("Categoria", [
                "Procuração", 
                "Contrato", 
                "Petição", 
                "Declaração", 
                "Recibo",
                "Notificação",
                "Outros"
            ])
            
            with st.expander("ℹ️ Ver códigos (variáveis) disponíveis"):
                st.markdown("""
                **Copie e cole estes códigos no seu texto:**
                
                **Dados do Cliente:**
                * `{nome}` : Nome Completo
                * `{nacionalidade}` : Nacionalidade
                * `{estado_civil}` : Estado Civil
                * `{profissao}` : Profissão
                * `{cpf}` ou `{cnpj}` : CPF/CNPJ
                * `{rg}` : RG
                * `{email}` : E-mail
                * `{telefone}` : Telefone
                
                **Endereço:**
                * `{endereco_completo}` : Endereço + Nº + Bairro + Cidade/UF
                * `{endereco}` : Logradouro
                * `{numero_casa}` : Número
                * `{bairro}` : Bairro
                * `{cidade}` : Cidade
                * `{estado}` : Estado
                * `{cep}` : CEP
                
                **Datas:**
                * `{data_atual}` : Data de hoje (DD/MM/AAAA)
                * `{data_extenso}` : Data por extenso (Ex: 09 de dezembro de 2025)
                """)
            
            conteudo = st.text_area(
                "Conteúdo do Modelo", 
                height=300, 
                placeholder="Eu, {nome}, {nacionalidade}, {estado_civil}, {profissao}, portador(a) do CPF nº {cpf} e RG nº {rg}, residente e domiciliado(a) em {endereco_completo}..."
            )
            
            if st.form_submit_button("💾 Salvar Modelo", type="primary"):
                if titulo and conteudo:
                    db.salvar_modelo_documento(titulo, categoria, conteudo)
                    st.success("Modelo salvo com sucesso!")
                    st.rerun()
                else:
                    st.error("Preencha título e conteúdo.")
    
    st.divider()
    
    # Listar Modelos Existentes
    df_modelos = db.sql_get("modelos_documentos", "titulo")
    
    if df_modelos.empty:
        st.info("Nenhum modelo cadastrado. Crie seu primeiro modelo acima!")
        return
    
    # Métricas
    col1, col2 = st.columns(2)
    col1.metric("Total de Modelos", len(df_modelos))
    categorias = df_modelos['categoria'].nunique() if 'categoria' in df_modelos.columns else 0
    col2.metric("Categorias", categorias)
    
    st.divider()
    
    # Listar por categoria
    if 'categoria' in df_modelos.columns:
        for categoria in df_modelos['categoria'].unique():
            modelos_cat = df_modelos[df_modelos['categoria'] == categoria]
            with st.expander(f"📁 {categoria} ({len(modelos_cat)} modelo(s))"):
                for _, row in modelos_cat.iterrows():
                    col1, col2 = st.columns([4, 1])
                    col1.write(f"**{row['titulo']}**")
                    col1.caption(f"Criado em: {row.get('criado_em', 'N/A')}")
                    
                    if col2.button("🗑️", key=f"del_mod_{row['id']}", help="Excluir modelo"):
                        db.excluir_modelo_documento(row['id'])
                        st.success("Modelo excluído!")
                        st.rerun()
    else:
        st.dataframe(df_modelos[['titulo', 'criado_em']], use_container_width=True)


def render_historico_documentos():
    """Exibe histórico de documentos gerados."""
    st.markdown("### 📚 Histórico de Documentos Gerados")
    
    # Buscar histórico
    historico = db.sql_get_query("""
        SELECT h.*, c.nome as cliente_nome
        FROM documentos_historico h
        LEFT JOIN clientes c ON h.id_cliente = c.id
        ORDER BY h.criado_em DESC
        LIMIT 50
    """)
    
    if historico.empty:
        st.info("Nenhum documento gerado ainda. Use o Gerador para criar documentos!")
        
        # Tentar criar tabela se não existir
        criar_tabela_historico()
        return
    
    # Filtros
    col1, col2 = st.columns(2)
    with col1:
        clientes = ["Todos"] + historico['cliente_nome'].dropna().unique().tolist()
        filtro_cliente = st.selectbox("Filtrar por Cliente", clientes)
    
    with col2:
        categorias = ["Todas"] + historico['categoria'].dropna().unique().tolist()
        filtro_categoria = st.selectbox("Filtrar por Categoria", categorias)
    
    # Aplicar filtros
    df_filtrado = historico.copy()
    if filtro_cliente != "Todos":
        df_filtrado = df_filtrado[df_filtrado['cliente_nome'] == filtro_cliente]
    if filtro_categoria != "Todas":
        df_filtrado = df_filtrado[df_filtrado['categoria'] == filtro_categoria]
    
    st.divider()
    st.caption(f"Exibindo {len(df_filtrado)} documento(s)")
    
    # Listar documentos
    for _, doc in df_filtrado.iterrows():
        with st.expander(f"📄 {doc['modelo_nome']} - {doc['cliente_nome']} ({doc['criado_em'][:10]})"):
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**Categoria:** {doc['categoria']}")
                st.write(f"**Cliente:** {doc['cliente_nome']}")
                st.write(f"**Gerado em:** {doc['criado_em']}")
                
                if doc.get('link_drive'):
                    st.markdown(f"🔗 [Abrir no Drive]({doc['link_drive']})")
            
            with col2:
                # Download do conteúdo
                if doc.get('conteudo'):
                    st.download_button(
                        "📥 Download",
                        data=doc['conteudo'],
                        file_name=f"{doc['modelo_nome']}_{doc['cliente_nome']}.txt",
                        mime="text/plain",
                        key=f"dl_hist_{doc['id']}"
                    )
            
            # Mostrar preview do conteúdo
            if doc.get('conteudo'):
                with st.expander("Ver Conteúdo"):
                    st.text_area("", value=doc['conteudo'], height=200, disabled=True, key=f"prev_{doc['id']}")


def render_upload_drive():
    """Upload de documentos para o Google Drive."""
    st.markdown("### 📤 Upload para Google Drive")
    
    if not DRIVE_DISPONIVEL:
        st.error("Módulo google_drive não disponível. Verifique a instalação.")
        return
    
    # Verificar autenticação
    try:
        service = gd.autenticar()
        if not service:
            st.error("Não foi possível conectar ao Google Drive. Verifique as credenciais.")
            return
        st.success("✅ Conectado ao Google Drive")
    except Exception as e:
        st.error(f"Erro na autenticação: {e}")
        return
    
    st.divider()
    
    # Upload de arquivo
    st.markdown("#### 📁 Upload de Arquivo")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Selecionar cliente para vincular
        df_clientes = db.sql_get("clientes", "nome")
        opcoes_clientes = ["(Sem vínculo)"] + (df_clientes['nome'].tolist() if not df_clientes.empty else [])
        cliente_vinculo = st.selectbox("Vincular a Cliente (opcional)", opcoes_clientes)
    
    with col2:
        # Categoria do documento
        categoria = st.selectbox("Categoria", [
            "Procuração",
            "Contrato",
            "Petição",
            "Declaração",
            "Comprovante",
            "Outros"
        ])
    
    # Upload do arquivo
    arquivo = st.file_uploader(
        "Escolha o arquivo",
        type=['pdf', 'docx', 'doc', 'txt', 'jpg', 'png', 'jpeg'],
        help="Formatos aceitos: PDF, Word, TXT, Imagens"
    )
    
    if arquivo:
        st.write(f"**Arquivo:** {arquivo.name} ({arquivo.size / 1024:.1f} KB)")
        
        if st.button("📤 Enviar para Drive", type="primary"):
            with st.spinner("Enviando arquivo..."):
                # Salvar temporariamente
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(arquivo.name)[1]) as tmp:
                    tmp.write(arquivo.getvalue())
                    tmp_path = tmp.name
                
                try:
                    # Upload para Drive
                    file_id, link = gd.upload_file(service, tmp_path)
                    
                    if file_id and link:
                        # Salvar no banco
                        id_cliente = None
                        if cliente_vinculo != "(Sem vínculo)":
                            cliente_data = df_clientes[df_clientes['nome'] == cliente_vinculo]
                            if not cliente_data.empty:
                                id_cliente = int(cliente_data.iloc[0]['id'])
                        
                        db.crud_insert("documentos_drive", {
                            "nome_arquivo": arquivo.name,
                            "tipo_arquivo": categoria,
                            "drive_id": file_id,
                            "web_link": link,
                            "id_cliente": id_cliente,
                            "data_upload": datetime.now().isoformat()
                        })
                        
                        st.success(f"✅ Arquivo enviado com sucesso!")
                        st.markdown(f"🔗 [Abrir no Drive]({link})")
                    else:
                        st.error("Erro ao enviar arquivo para o Drive.")
                except Exception as e:
                    st.error(f"Erro: {e}")
                finally:
                    # Limpar arquivo temporário
                    if os.path.exists(tmp_path):
                        os.remove(tmp_path)


# === FUNÇÕES AUXILIARES ===

def gerar_pdf(texto: str, titulo: str = "Documento", cliente: str = "", incluir_assinatura: bool = False) -> bytes:
    """
    Gera um PDF formatado a partir de texto usando ReportLab.
    
    Args:
        texto: Conteúdo do documento
        titulo: Título do documento (usado no cabeçalho)
        cliente: Nome do cliente (usado no cabeçalho)
        incluir_assinatura: Se True, adiciona campo para assinatura digital
    
    Returns:
        bytes: Conteúdo do PDF em bytes
    """
    buffer = io.BytesIO()
    
    # Criar documento
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    # Estilos
    styles = getSampleStyleSheet()
    
    # Estilo do título
    estilo_titulo = ParagraphStyle(
        'Titulo',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=12,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # Estilo do subtítulo (cliente)
    estilo_subtitulo = ParagraphStyle(
        'Subtitulo',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor='#666666'
    )
    
    # Estilo do corpo
    estilo_corpo = ParagraphStyle(
        'Corpo',
        parent=styles['Normal'],
        fontSize=11,
        leading=16,
        alignment=TA_JUSTIFY,
        spaceAfter=12,
        fontName='Helvetica'
    )
    
    # Estilo para assinatura
    estilo_assinatura = ParagraphStyle(
        'Assinatura',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_CENTER,
        spaceBefore=40
    )
    
    # Construir elementos do PDF
    elementos = []
    
    # Cabeçalho
    elementos.append(Paragraph(titulo, estilo_titulo))
    if cliente:
        elementos.append(Paragraph(f"Cliente: {cliente}", estilo_subtitulo))
    elementos.append(Spacer(1, 0.5*cm))
    
    # Corpo do documento - dividir em parágrafos
    paragrafos = texto.split('\n\n')
    for paragrafo in paragrafos:
        if paragrafo.strip():
            # Substituir quebras de linha simples por espaços
            texto_limpo = paragrafo.replace('\n', ' ').strip()
            # Escapar caracteres especiais do HTML
            texto_limpo = texto_limpo.replace('&', '&amp;')
            texto_limpo = texto_limpo.replace('<', '&lt;')
            texto_limpo = texto_limpo.replace('>', '&gt;')
            elementos.append(Paragraph(texto_limpo, estilo_corpo))
    
    # Campo de assinatura (opcional)
    if incluir_assinatura:
        elementos.append(Spacer(1, 2*cm))
        
        # Linha de assinatura
        elementos.append(Paragraph("_" * 50, estilo_assinatura))
        elementos.append(Paragraph("<b>ASSINATURA DIGITAL</b>", estilo_assinatura))
        elementos.append(Spacer(1, 0.3*cm))
        
        # Data e local
        data_atual = datetime.now().strftime('%d/%m/%Y')
        elementos.append(Paragraph(f"Data: {data_atual}", estilo_assinatura))
        elementos.append(Spacer(1, 0.5*cm))
        
        # Instrução para token
        estilo_instrucao = ParagraphStyle(
            'Instrucao',
            parent=styles['Normal'],
            fontSize=8,
            alignment=TA_CENTER,
            textColor='#888888'
        )
        elementos.append(Paragraph(
            "Para assinar com certificado digital (Token OAB): Abra este PDF no Adobe Acrobat Reader → "
            "Ferramentas → Certificados → Assinar Digitalmente → Selecione o campo acima",
            estilo_instrucao
        ))
    
    # Gerar PDF
    doc.build(elementos)
    
    # Retornar bytes
    buffer.seek(0)
    return buffer.getvalue()


def formatar_data_extenso(data: datetime) -> str:
    """Formata data por extenso (Ex: 09 de dezembro de 2025)."""
    meses = [
        "", "janeiro", "fevereiro", "março", "abril", "maio", "junho",
        "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"
    ]
    return f"{data.day} de {meses[data.month]} de {data.year}"


def salvar_documento_historico(id_cliente, cliente_nome, modelo_nome, categoria, conteudo, link_drive=None):
    """Salva documento gerado no histórico."""
    # Garantir que a tabela existe
    criar_tabela_historico()
    
    db.crud_insert("documentos_historico", {
        "id_cliente": id_cliente,
        "modelo_nome": modelo_nome,
        "categoria": categoria,
        "conteudo": conteudo,
        "link_drive": link_drive,
        "criado_em": datetime.now().isoformat()
    })


def criar_tabela_historico():
    """Cria tabela de histórico de documentos se não existir."""
    try:
        db.sql_run("""
            CREATE TABLE IF NOT EXISTS documentos_historico (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                id_cliente INTEGER REFERENCES clientes(id),
                modelo_nome TEXT,
                categoria TEXT,
                conteudo TEXT,
                link_drive TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
    except Exception as e:
        pass  # Tabela pode já existir
