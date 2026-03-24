# Saude - App de Teste

## Visao geral
Aplicacao minima de clinica para validar segregacao de acesso, privacidade de dados e controle de documentos/prontuario.

## Atores
- Paciente
- Profissional
- Administrador

## Fluxos principais
- Login/cadastro
- Agendamento de consulta
- Cancelamento de consulta
- Upload/listagem de documentos
- Visualizacao de prontuario
- Notificacoes mockadas

## Ativos criticos
- Prontuario
- Documentos clinicos
- Agenda de consultas
- Identidade de paciente e profissional

## Dados sensiveis
- Dados de saude
- Documentos com informacoes clinicas

## Integracoes
- Gateway de notificacao mockado

## Trust boundaries
- Internet
- Aplicacao clinica
- Dados clinicos
- Integracao de notificacao

## Regras de negocio criticas
- Paciente ve apenas o proprio prontuario/documentos.
- Profissional acessa prontuario apenas com vinculo de consulta.
- Admin possui visao operacional.
- Notificacoes nao devem expor dados sensiveis em excesso.
- Alteracao de prontuario e permitida apenas para profissional/admin.
- Cancelamento deve respeitar ownership do agendamento por papel.
- Bloqueios de acesso devem ser auditaveis (`audit_log`).

## Cenarios obrigatorios de teste
- Agendamento e cancelamento por paciente
- Acesso de prontuario por profissional vinculado
- Bloqueio de acesso indevido entre pacientes
- Upload e listagem de documentos
- Notificacao de eventos sem vazamento de dados clinicos
- Tentativa de prontuario sem vinculo por paciente/profissional bloqueada
- Tentativa de listar documentos de terceiro bloqueada
- Notificacao reduzida a metadado operacional (sem ids sensiveis de ator)
- Evidencia de bloqueios por papel em trilha de auditoria

## Riscos esperados mais relevantes
- Exposicao indevida de prontuario
- Quebra de segregacao entre papeis
- Vazamento de dados em notificacao/log
- Enumeracao de documentos

## Attack Tree (resumo)
### Acesso a dados sensiveis (privacidade)
- Objetivo: ler prontuario sem autorizacao
- Caminhos:
  - bypass de role check
  - manipular identificador de paciente
  - abuso de sessao/profissional sem vinculo clinico
  - confusao de fronteira entre papeis (patient/professional/admin)

### Notificacoes
- Objetivo: exfiltrar dado sensivel por canal auxiliar
- Caminhos:
  - payload com PII excessiva
  - log sem mascaramento
  - destinatario incorreto
  - vazamento indireto por metadado sensivel em evento
