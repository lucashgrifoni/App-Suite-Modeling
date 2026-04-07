"""
Padrão único de identificadores para entidades no documento canónico.

Inclui componentes, fluxos, ativos, ameaças, fronteiras, etc. Os campos
``name`` / ``title`` humanos continuam sem regex restritiva no schema;
apenas ``id`` e chaves similares usam este padrão.

Regras:

- Primeiro carácter: letra ASCII, dígito ou ``_`` (não ``.`` nem ``-``,
  para evitar ambiguidade em YAML e alguns serializadores).
- Seguintes: letras ASCII, dígitos, ``_``, ``-``, ``.``.

Exemplos válidos: ``x_x_x``, ``api``, ``api.v1``, ``svc-2``, ``42east``, ``_gate``.

Excluídos de propósito: espaços, ``/``, ``\\``, ``<``, ``>``, unicode em IDs
(reduz surpresas em export Mermaid, ficheiros e APIs).
"""

from __future__ import annotations

ENTITY_ID_PATTERN = r"^[a-zA-Z0-9_][a-zA-Z0-9_.-]*$"

__all__ = ["ENTITY_ID_PATTERN"]
