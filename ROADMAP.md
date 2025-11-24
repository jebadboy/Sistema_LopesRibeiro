# 🗺️ Roadmap de Evolução - Sistema Lopes Ribeiro

## 📋 Visão Geral

Este documento apresenta o plano completo de evolução do Sistema Lopes Ribeiro, baseado nas sugestões de melhoria "Nível Astrea" para os 5 módulos principais.

**Status**: Em Planejamento  
**Última Atualização**: 2025-11-23  
**Responsável**: Equipe de Desenvolvimento

---

## 🎯 Priorização

### Alta Prioridade (Implementar Primeiro)
1. **Módulo de Processos** - Timeline de andamentos, documentos chave, vínculos
2. **Módulo de Agenda** - Tarefas, responsáveis, calendário visual
3. **Módulo Financeiro** - Repasse de parceria, recorrências, parcelamentos

### Média Prioridade
4. **Módulo de Propostas** - Status/funil, modelos
5. **Módulo de Relatórios** - Exportação Excel, relatórios específicos

### Baixa Prioridade (Futuro)
6. **Integração com IA** - Assistente inteligente
7. **Melhorias Gerais** - Backup completo, otimizações

---

## 📊 Módulo por Módulo

### 1️⃣ PROCESSOS

#### Andamento Processual (Timeline) ⭐ CRÍTICO
- **O que é**: Linha do tempo dentro de cada processo
- **Como funciona**: Adicionar atualizações cronológicas (ex: "Petição protocolada", "Concluso para decisão")
- **Impacto**: ⬆️⬆️⬆️ (Coração da gestão jurídica)
- **Complexidade**: 🔧🔧 (Média)

#### Documentos Chave
- **O que é**: Links específicos para documentos importantes
- **Como funciona**: Botões clicáveis para Petição Inicial, Procuração, Sentença
- **Impacto**: ⬆️⬆️ (Facilita acesso rápido)
- **Complexidade**: 🔧 (Baixa)

#### Vínculo com Financeiro
- **O que é**: Aba que lista contas vinculadas ao processo
- **Como funciona**: Exibição automática de contas a receber/pagar do processo
- **Impacto**: ⬆️⬆️ (Visão integrada)
- **Complexidade**: 🔧🔧 (Média)

#### Vínculo com Agenda
- **O que é**: Aba que lista prazos e audiências do processo
- **Como funciona**: Exibição automática de eventos da agenda vinculados
- **Impacto**: ⬆️⬆️ (Visão integrada)
- **Complexidade**: 🔧🔧 (Média)

#### Classificação de Status
- **O que é**: Campo para marcar processo como ATIVO/FINALIZADO/SOBRESTADO
- **Como funciona**: Dropdown de seleção
- **Impacto**: ⬆️ (Organização)
- **Complexidade**: 🔧 (Baixa)

#### Sinalização de Inadimplência
- **O que é**: Badge visual se cliente está com parcela vencida
- **Como funciona**: Verificação automática ao abrir processo
- **Impacto**: ⬆️⬆️ (Alerta importante)
- **Complexidade**: 🔧 (Baixa - já existe função)

---

### 2️⃣ AGENDA

#### Adicionar "Tarefas" ⭐ IMPORTANTE
- **O que é**: Terceiro tipo de evento além de Prazos e Audiências
- **Como funciona**: Para atividades internas (elaborar petição, ligar para cliente)
- **Impacto**: ⬆️⬆️⬆️ (Gestão completa do tempo)
- **Complexidade**: 🔧🔧 (Média)

#### Campo "Responsável"
- **O que é**: Atribuir quem é responsável por cada tarefa/prazo
- **Como funciona**: Campo de seleção (Eduardo, Dra. Sheila, etc)
- **Impacto**: ⬆️⬆️⬆️ (Vital para Dashboard)
- **Complexidade**: 🔧 (Baixa)

#### Visualização em Calendário
- **O que é**: Botão para ver eventos em calendário mensal visual
- **Como funciona**: Biblioteca de calendário interativo
- **Impacto**: ⬆️⬆️⬆️ (Experiência incrível)
- **Complexidade**: 🔧🔧🔧 (Alta)

#### Filtro por Responsável
- **O que é**: Filtrar agenda por pessoa
- **Como funciona**: "Só tarefas de Eduardo" ou "Só da Dra. Sheila"
- **Impacto**: ⬆️⬆️ (Produtividade)
- **Complexidade**: 🔧 (Baixa)

#### Integração com Google Calendar
- **O que é**: Sincronizar com agenda do Google
- **Como funciona**: API do Google Calendar
- **Impacto**: ⬆️⬆️⬆️ (Controle real do dia)
- **Complexidade**: 🔧🔧🔧 (Alta - requer OAuth)

#### Vínculo com Financeiro
- **O que é**: Tarefas relacionadas a finanças (emitir boleto)
- **Como funciona**: Link entre tarefa e lançamento financeiro
- **Impacto**: ⬆️ (Integração)
- **Complexidade**: 🔧🔧 (Média)

#### Sistema de Cores
- **O que é**: Cores para diferenciar tipos/prioridades
- **Como funciona**: Legenda de cores (Vermelho=Urgente, Amarelo=Importante, etc)
- **Impacto**: ⬆️ (Visual)
- **Complexidade**: 🔧 (Baixa)

---

### 3️⃣ FINANCEIRO

#### Cálculo de Repasse de Parceria ⭐ IMPORTANTE
- **O que é**: Ao receber pagamento, criar automaticamente conta a pagar do parceiro
- **Como funciona**: Sistema calcula percentual e sugere lançamento
- **Impacto**: ⬆️⬆️⬆️ (Automação valiosa)
- **Complexidade**: 🔧🔧 (Média)

#### Lançamentos Recorrentes
- **O que é**: Despesas que se repetem todo mês
- **Como funciona**: Marcar como "Recorrente" e sistema lança automaticamente
- **Impacto**: ⬆️⬆️ (Economia de tempo)
- **Complexidade**: 🔧🔧 (Média - requer scheduler)

#### Anexar Comprovantes
- **O que é**: Link do comprovante de pagamento em cada lançamento
- **Como funciona**: Campo com link do Drive (clicável)
- **Impacto**: ⬆️ (Organização)
- **Complexidade**: 🔧 (Baixa)

#### Tabela de Parcelamento
- **O que é**: Sistema de parcelas
- **Como funciona**: Criar N parcelas, acompanhar status individual
- **Impacto**: ⬆️⬆️ (Controle detalhado)
- **Complexidade**: 🔧🔧 (Média)

#### Formas de Pagamento
- **O que é**: Registrar se foi PIX, Dinheiro, Cartão, Parcelamento
- **Como funciona**: Campo de seleção
- **Impacto**: ⬆️ (Informação)
- **Complexidade**: 🔧 (Baixa)

#### Entrada + Êxito vs Apenas Êxito
- **O que é**: Diferenciar tipos de honorários
- **Como funciona**: Campo para marcar tipo de processo
- **Impacto**: ⬆️ (Categorização)
- **Complexidade**: 🔧 (Baixa)

---

### 4️⃣ PROPOSTAS

#### Status da Proposta (Funil de Vendas)
- **O que é**: Acompanhar estágio da negociação
- **Como funciona**: Status: Em negociação / Enviada / Aceita / Recusada
- **Impacto**: ⬆️⬆️ (Gestão comercial)
- **Complexidade**: 🔧 (Baixa)

#### Modelos de Proposta
- **O que é**: Templates pré-prontos
- **Como funciona**: Botão "Usar Modelo" que preenche campos padrões
- **Impacto**: ⬆️⬆️ (Agilidade)
- **Complexidade**: 🔧🔧 (Média)

#### Relatório de Conversão
- **O que é**: Quantas propostas viraram processos
- **Como funciona**: Relatório com taxa de conversão
- **Impacto**: ⬆️⬆️ (Métrica comercial)
- **Complexidade**: 🔧 (Baixa)

---

### 5️⃣ RELATÓRIOS

#### Exportar para Excel (CSV)
- **O que é**: Botão para baixar dados
- **Como funciona**: Gerar arquivo CSV/XLSX de cada tabela
- **Impacto**: ⬆️⬆️ (Análise externa)
- **Complexidade**: 🔧 (Baixa)

#### Relatório de Inadimplência
- **O que é**: Lista de clientes com pagamentos atrasados
- **Como funciona**: Relatório dedicado com valor total em aberto
- **Impacto**: ⬆️⬆️⬆️ (Gestão financeira)
- **Complexidade**: 🔧 (Baixa)

#### Relatório de Comissões
- **O que é**: Todos os pagamentos a parceiros
- **Como funciona**: Lista filtrada por período
- **Impacto**: ⬆️⬆️ (Controle de parcerias)
- **Complexidade**: 🔧 (Baixa)

#### Backup Completo
- **O que é**: Salvar TODOS os dados do sistema
- **Como funciona**: Exportar todas as tabelas (SQLite + CSV)
- **Impacto**: ⬆️⬆️⬆️ (Segurança)
- **Complexidade**: 🔧🔧 (Média)

---

### 6️⃣ IA JURÍDICA

#### Assistente IA no Sistema
- **O que é**: IA integrada para ajudar com dúvidas e tarefas
- **Como funciona**: Chat dentro do sistema com contexto dos dados
- **Impacto**: ⬆️⬆️⬆️ (Inovação)
- **Complexidade**: 🔧🔧🔧🔧 (Muito Alta)

#### Análise de Estratégia
- **O que é**: IA sugere melhor abordagem para cliente/processo
- **Como funciona**: Análise de documentos e histórico
- **Impacto**: ⬆️⬆️ (Valor agregado)
- **Complexidade**: 🔧🔧🔧🔧 (Muito Alta)

---

## 📅 Cronograma Sugerido

### Sprint 1 (Semanas 1-2)
- ✅ Preparação do banco de dados (novas tabelas)
- ✅ Módulo de Processos: Timeline de andamentos
- ✅ Módulo de Processos: Documentos chave e vínculos

### Sprint 2 (Semanas 3-4)
- ✅ Módulo de Agenda: Adicionar tarefas e responsável
- ✅ Módulo de Agenda: Filtros e cores

### Sprint 3 (Semanas 5-6)
- ✅ Módulo Financeiro: Repasse de parceria
- ✅ Módulo Financeiro: Parcelamentos
- ✅ Módulo Financeiro: Recorrências

### Sprint 4 (Semanas 7-8)
- ✅ Módulo de Propostas: Status e modelos
- ✅ Módulo de Relatórios: Exportação e relatórios específicos

### Sprint 5 (Semanas 9-10)
- ✅ Módulo de Agenda: Visualização em calendário
- ✅ Módulo de Agenda: Integração Google Calendar (opcional)

### Sprint 6+ (Futuro)
- ⏳ Integração com IA
- ⏳ Melhorias contínuas

---

## 🛠️ Dependências Técnicas

### Bibliotecas Python Necessárias
```
google-auth==2.27.0
google-auth-oauthlib==1.2.0
google-api-python-client==2.116.0
streamlit-calendar==0.9.0
openpyxl==3.1.2
schedule==1.2.0
```

### Serviços Externos
- Google Cloud Console (para Google Calendar API)
- Google Gemini API (para IA - já configurado)

---

## 📝 Notas de Implementação

1. **Banco de Dados**: Todas as alterações serão feitas com migrations seguras (ALTER TABLE quando possível)
2. **Compatibilidade**: Manter funcionalidades atuais durante transição
3. **Testes**: Cada módulo será testado antes de deploy
4. **Backup**: Criar backup antes de cada alteração major
5. **Documentação**: Atualizar README com novas funcionalidades

---

## 🔄 Status de Implementação

| Módulo | Status | Progresso |
|--------|--------|-----------|
| Processos | 🔴 Não iniciado | 0% |
| Agenda | 🔴 Não iniciado | 0% |
| Financeiro | 🔴 Não iniciado | 0% |
| Propostas | 🔴 Não iniciado | 0% |
| Relatórios | 🔴 Não iniciado | 0% |
| IA | 🔴 Não iniciado | 0% |

**Legenda**:
- 🔴 Não iniciado
- 🟡 Em andamento
- 🟢 Concluído
- 🔵 Em revisão

---

## 📞 Próximos Passos

1. ✅ Revisar este roadmap
2. ✅ Aprovar plano de implementação
3. ⏸️ Definir prioridades finais
4. ⏸️ Iniciar Sprint 1

**Última revisão**: 2025-11-23
