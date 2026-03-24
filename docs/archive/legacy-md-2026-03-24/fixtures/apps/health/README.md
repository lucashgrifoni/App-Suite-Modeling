# App de Teste - Saude

## Descricao do dominio
Aplicacao simplificada de clinica para agendamento, cancelamento e prontuario leve com documentos.

## Atores
- Paciente
- Profissional
- Administrador

## Funcionalidades
- Cadastro/login
- Perfil de paciente e profissional
- Agendamento e cancelamento de consulta
- Upload/listagem de documentos
- Visualizacao simples de prontuario
- Notificacoes mockadas

## Dados sensiveis
- Prontuario e notas clinicas
- Documentos de paciente
- Dados de agenda

## Integracoes externas mockadas
- Gateway de notificacoes (sem envio real)

## Trust boundaries principais
- Internet (papeis humanos)
- Aplicacao clinica
- Dados clinicos/documentos
- Notificacao externa

## Premissas
- Controle de acesso simplificado por papel e vinculo de consulta
- Armazenamento local de documentos para inspeção

## Fora de escopo
- Telemedicina real
- Assinatura digital de laudos
- Integracao com sistemas hospitalares externos

## Execucao local
```bash
python fixtures/apps/health/app.py
```
