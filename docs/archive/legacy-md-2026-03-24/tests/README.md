# Testes

- **`tests/`** na raiz: testes de integração e do schema canônico (exemplos em `examples/`).
- Ferramenta: **pytest** (`python -m pytest`).

Testes unitários específicos de um pacote podem, no futuro, residir em `packages/<nome>/tests/` se o volume justificar; o importante é não duplicar fixtures sem necessidade.
