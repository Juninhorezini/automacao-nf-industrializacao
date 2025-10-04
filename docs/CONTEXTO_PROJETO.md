# 📚 CONTEXTO COMPLETO DO PROJETO

## 🎯 Visão Geral
Sistema de automação para emissão de NF-e de industrialização integrado com Google Sheets e API Bling.

## 🏗️ Arquitetura

### Componentes Principais:
1. **Google Sheets** - Armazena dados dos produtos e configurações
2. **API Bling** - Emite as notas fiscais
3. **Script Python** - Orquestra todo o processo

### Abas da Planilha:
- **DadosXML**: Produtos industrializados
- **Config_DePara**: Mapeamento de códigos
- **Config_Valores**: Valores unitários
- **Config_NotasEntrada**: Controle FIFO de estoque

## 📋 Fluxo de Execução

1. Ler produtos da aba DadosXML
2. Verificar Config_DePara (produtos aptos)
3. Buscar valores em Config_Valores
4. Consumir saldo FIFO de Config_NotasEntrada
5. Emitir NF de Retorno (CFOP 5902)
6. Emitir NF de Industrialização (CFOP 5124)
7. Atualizar saldos e status

## 🔧 Configurações

Ver arquivo `config/automacao_config.json`

## ⚠️ Status Atual

✅ Script completo (494 linhas)
✅ Integração Google Sheets funcionando
✅ API Bling conectada
⚠️ Aguardando preenchimento de Config_DePara

## 📝 Para Retomar em Novos Chats

**Diga ao Rube:**
"Acesse meu projeto: https://github.com/Juninhorezini/automacao-nf-industrializacao"

O Rube lerá este arquivo e entenderá todo o contexto!
