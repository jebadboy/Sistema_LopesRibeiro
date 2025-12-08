# Guia de Testes - Fase 3: Funcionalidades do Módulo Clientes

## Objetivo

Testar todas as funcionalidades principais do módulo de Clientes para garantir que estão funcionando corretamente após as correções das Fases 1 e 2.

---

## Preparação

### 1. Iniciar o Sistema

```bash
cd "H:\Meu Drive\automatizacao\Sistema_LopesRibeiro"
python app.py
```

Aguarde o sistema abrir no navegador (geralmente em <http://localhost:8501>)

### 2. Fazer Login

- Faça login com suas credenciais
- Navegue até o módulo **Clientes** no menu lateral

---

## Bateria de Testes

### Teste 1: Cadastro de Novo Cliente ✓

**Objetivo**: Verificar se é possível cadastrar um novo cliente com todos os campos

#### Passos

1. Abra a aba **"Novo Cadastro"**
2. Preencha os campos:
   - **Tipo de Pessoa**: Física
   - **Nome**: João da Silva Teste
   - **CPF**: 12345678901 (apenas números)
   - **Fase**: EM NEGOCIAÇÃO
   - **E-mail**: <joao.teste@email.com>
   - **WhatsApp**: 11987654321
   - **Fixo**: 1133334444
   - **Profissão**: Engenheiro
   - **Estado Civil**: Casado(a)

3. Preencha o endereço:
   - **CEP**: 01310100
   - Clique em **"Buscar CEP"**
   - Verifique se os campos foram preenchidos automaticamente
   - **Número**: 1000
   - **Complemento**: Apto 101

4. Complete os dados internos:
   - **Link Drive**: (pode deixar em branco por enquanto)
   - **Obs**: Cliente de teste - Fase 3

5. Clique em **"SALVAR CLIENTE"**

#### Resultado Esperado

- ✅ Mensagem de sucesso "Cliente João da Silva Teste Salvo!"
- ✅ Campos do formulário limpos
- ✅ Cliente aparece na listagem

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 2: Buscar e Visualizar Cliente ✓

**Objetivo**: Verificar se o cliente cadastrado aparece na listagem

#### Passos

1. Vá para a aba **"Base / Editar / Propostas"**
2. Use a busca: digite "João"
3. Verifique se o cliente "João da Silva Teste" aparece
4. Selecione o cliente no dropdown "Ficha do Cliente"

#### Resultado Esperado

- ✅ Cliente aparece na busca
- ✅ Card de cabeçalho exibe nome e dados formatados
- ✅ CPF formatado como XXX.XXX.XXX-XX
- ✅ Timeline vazia ou com evento "Cliente Cadastrado"

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 3: Editar Dados Cadastrais ✓

**Objetivo**: Verificar se é possível editar dados do cliente

#### Passos

1. Com o cliente "João da Silva Teste" selecionado
2. Expanda **"Editar Dados Cadastrais"**
3. Altere:
   - **Status**: ATIVO
   - **Telefone**: 11999999999
   - **Cidade**: São Paulo (se não estiver)
4. Clique em **"Salvar Alterações"**

#### Resultado Esperado

- ✅ Mensagem "Dados atualizados com sucesso!"
- ✅ Página recarrega
- ✅ Dados alterados são exibidos corretamente
- ✅ Status mudou para "ATIVO"

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 4: Geração de Proposta ✓

**Objetivo**: Testar criação e geração de documento de Proposta

#### Passos

1. Com o cliente selecionado
2. Expanda **"Proposta e Negociação"**
3. Preencha:
   - **Valor Total**: 15000
   - **Entrada**: 5000
   - **Parcelas**: 10
   - **Pagamento**: Parcelado Mensal
   - **Vencimento 1ª Parcela**: (selecione uma data futura)
   - **Objeto**: Ação de Indenização por Danos Morais

4. Clique em **"Salvar e Atualizar DOC"**
5. Após salvar, clique em **"Baixar DOC Proposta"**

#### Resultado Esperado

- ✅ Mensagem "Proposta salva e documento atualizado!"
- ✅ Arquivo .docx baixado
- ✅ Abrir o arquivo e verificar se contém os dados corretos

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 5: Geração de Documentos (Procuração e Hipossuficiência) ✓

**Objetivo**: Testar geração de documentos legais

#### Passos

**5.1 - Procuração**

1. Expanda **"Documentação e Modelos"**
2. Expanda **"Procuração"**
3. Marque **"Incluir Poderes Especiais"**
4. Clique em **"Gerar Procuração (DOC)"**
5. Clique em **"Baixar Procuração"**

**5.2 - Hipossuficiência**

1. Expanda **"Declaração de Hipossuficiência"**
2. Clique em **"Gerar Declaração (DOC)"**
3. Clique em **"Baixar Declaração"**

**5.3 - Contrato**

1. Expanda **"Contrato de Honorários"**
2. Clique em **"Gerar Contrato (DOC)"**
3. Clique em **"Baixar Contrato"**

#### Resultado Esperado

- ✅ 3 arquivos .docx baixados
- ✅ Cada arquivo se abre sem erro
- ✅ Documentos contêm dados do cliente

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 6: Timeline do Cliente ✓

**Objetivo**: Verificar se o sistema de timeline está funcionando

#### Passos

1. Com o cliente selecionado
2. Role até a seção **"Histórico do Cliente"**
3. Observe a timeline

#### Resultado Esperado

- ✅ Timeline exibe eventos (pode estar vazia se não houver triggers automáticos)
- ✅ Timeline tem CSS customizado (cores, ícones, layout moderno)
- ✅ Sem erros de SQL no console

**Nota**: O registro automático de eventos na timeline pode precisar de melhorias na Fase 5

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 7: Links do Google Drive ✓

**Objetivo**: Testar funcionalidade de links do Drive

#### Passos

1. Edite o cliente e adicione um link do Google Drive válido no campo **"Link Drive"**
   - Exemplo: <https://drive.google.com/drive/folders/seu_id>
2. Salve
3. Verifique se o link aparece:
   - No card de cabeçalho como "📂 Abrir Pasta no Drive"
   - Na listagem da aba "Base / Editar"

4. Clique no link

#### Resultado Esperado

- ✅ Link é salvo corretamente
- ✅ Link aparece no card de cabeçalho
- ✅ Link aparece na coluna "Drive" da tabela
- ✅ Clicar abre o Drive em nova aba

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

### Teste 8: Ações Rápidas ✓

**Objetivo**: Testar botões de ação rápida

#### Passos

1. Com cliente selecionado
2. Teste o botão **"Novo Processo"**
   - Deve redirecionar para módulo Processos
   - Nome do cliente deve estar pré-preenchido

3. Volte para Clientes e selecione o cliente novamente
4. Teste o botão **"Novo Lançamento"**
   - Deve redirecionar para módulo Financeiro
   - Nome do cliente deve estar pré-preenchido

#### Resultado Esperado

- ✅ Redirecionamento funciona
- ✅ Nome do cliente pré-preenchido nos módulos destino

#### Marcar como

- [ ] ✅ PASSOU
- [ ] ❌ FALHOU (anotar erro)

---

## Checklist Final

Após completar todos os testes, marque:

- [ ] Todos os 8 testes passaram sem erros
- [ ] Nenhum erro apareceu no console/terminal
- [ ] Sistema não travou ou apresentou lentidão
- [ ] Interface está responsiva e visual está correto

---

## Reportar Problemas

Se algum teste falhou, anote:

1. **Número do Teste**
2. **Passo onde falhou**
3. **Mensagem de erro** (se houver)
4. **Comportamento observado**
5. **Screenshot** (se aplicável)

---

## Próximos Passos

Após concluir a Fase 3:

- **Se todos passaram**: Prosseguir para Fase 4 (Integrações)
- **Se houve falhas**: Corrigir os problemas identificados antes de prosseguir
