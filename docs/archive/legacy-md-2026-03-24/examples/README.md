# Exemplos

Arquivos **Threat Modeling as Code** válidos para:

- testes automatizados (`tests/` referencia estes caminhos);
- documentação e onboarding;
- validação manual: `otm validate <arquivo>`.

## Convenção

- Extensão sugerida: `.otm.yaml`
- Devem passar na validação do schema atual (`otm_core_schema`)

## Lista

| Arquivo | Descrição |
|---------|-----------|
| `minimal.otm.yaml` | Cenário mínimo válido (schema v1) |
| `saas-ordering-v1.otm.yaml` | Exemplo realista: negócio, ativos, ameaças, mitigações, evidências, frameworks |
| `example-template-saas-web.otm.yaml` | Mesmo conteúdo do template CLI `saas-web` (referência) |
