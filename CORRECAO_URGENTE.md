# ⚠️ ERRO NA IMPLEMENTAÇÃO - CORRIGINDO

## Problema Detectado

Sua implementação manual teve **2 erros críticos**:

### ❌ Erro 1: database.py
- **O que aconteceu:** Todo o código foi colocado FORA de qualquer função
- **A função `inicializar_tabelas_v2()` foi deletada**
- **Resultado:** Sistema não func iona, código corrompido

### ❌ Erro 2: processos.py  
- **O que aconteceu:** Código foi adicionado no topo do arquivo (linhas 19-79)
- **Problema:** Está FORA de qualquer função, será executado ao importar o módulo
- **Variável `processo_id` não existe nesse contexto**
- **Resultado:** Erro fatal ao iniciar

---

## ✅ SOLUÇÃO SIMPLES

Restaurei os arquivos originais. Faça assim:

### database.py - Inserir APENAS estas 5 linhas

**Localização:** Linha 183, logo APÓS `inicializar_tabelas_v2()`

```python
            # Inicializar tabela de tokens públicos
            try:
                import token_manager
                token_manager.inicializar_tabela_tokens()
            except Exception as e:
                logger.warning(f"Erro ao inicializar tokens públicos: {e}")
```

**IMPORTANTE:** Deixar TODO o resto do arquivo intacto!

---

### processos.py - Inserir dentroda função

**Local CORRETO:** Dentro da função `render_gerenciar_processos()`, após exibir histórico do processo (aprox. linha 150)

```python
# Após mostrar históri

o, adicionar:

        # ===== LINK PÚBLICO =====
        import token_manager as tm
        
        st.markdown("---")
        st.markdown("### 🔗 Link Público de Consulta")
        
        col_token1, col_token2 = st.columns([2, 1])
        
        with col_token1:
            dias_validade = st.number_input(
                "Validade do link (dias)", 
                min_value=1,
                max_value=365, 
                value=30,
                help="Número de dias até o link expirar",
                key=f"dias_val_{pid}"
            )
        
        with col_token2:
            if st.button("Gerar Link Público", type="primary", use_container_width=True, key=f"gerar_{pid}"):
                token = tm.gerar_token_publico(pid, dias_validade)
                
                if token:
                    url_base = "http://localhost:8501"
                    link_publico = f"{url_base}/public_view?token={token}"
                    
                    st.session_state[f'link_gerado_{pid}'] = link_publico
                    st.session_state[f'token_validade_{pid}'] = dias_validade
                    st.success("Link gerado com sucesso!")
                    st.rerun()
        
        # Exibir link se foi gerado
        if f'link_gerado_{pid}' in st.session_state:
            st.code(st.session_state[f'link_gerado_{pid}'], language=None)
            
            st.info(
                f"📋 Copie este link e envie ao cliente por e-mail ou WhatsApp. "
                f"O link é válido por {st.session_state.get(f'token_validade_{pid}', 30)} dias."
            )
        
        # Listar tokens ativos
        st.markdown("#### Tokens Ativos Deste Processo")
        tokens_list = tm.listar_tokens_processo(pid)
        
        if tokens_list:
            for token_info in tokens_list:
                col1, col2, col3 = st.columns([3, 2, 1])
                
                with col1:
                    st.caption(f"Token: ...{token_info['token'][-10:]}")
                
                with col2:
                    status = "✅ Ativo" if token_info['ativo'] else "❌ Revogado"
                    acessos = token_info['acessos']
                    st.caption(f"{status} | Aces sos: {acessos}")
                
                with col3:
                    if token_info['ativo']:
                        if st.button("Revogar", key=f"revoke_{token_info['id']}"):
                            if tm.revogar_token_publico(token_info['token']):
                                st.success("Token revogado!")
                                st.rerun()
        else:
            st.caption("Nenhum token gerado ainda")
```

**IMPORTANTE:** 
- Use `pid` (variável que já existe na função)
- Adicione keys únicas nos elementos Streamlit
- Coloque DENTRO da função `render_gerenciar_processos()`

---

## 🎯 Ponto de Inserção Exato

Vou criar um arquivo de exemplo com os pontos exatos marcados.
