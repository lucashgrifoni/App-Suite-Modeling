## Análise automática (motor)

- Versão do motor: `0.1.0`
- Metodologia: `stride`
- Avisos estruturais: 0
- Achados de fronteira: 1
- Heurísticas base novas: 21
- Heurísticas base já cobertas: 0
- Ameaças do pack (novas): 0
- Ameaças do pack (já cobertas): 0
- Maior score heurístico (L×I): **25.0**

### Referências a frameworks (agregado)

Contagem de referências `framework:control_id` nas heurísticas (por catálogo canónico):

- **ISO/IEC 27001 (Annex A)** (`iso_27001`): 42
- **NIST CSF** (`nist_csf`): 39
- **OWASP ASVS** (`owasp_asvs`): 38
- **OWASP Threat Modeling** (`owasp_tm`): 21


### Fluxos entre fronteiras

- Fluxo 'http_in' liga fronteira 'internet' → 'vpc'.

### Qualidade do modelo e metodologia (resumo)

- **Pré-check:** score **72/100** (banda `good`) · confiança nas recomendações: `high` · fit STRIDE: `strong`.
- **Completude metodológica:** `complete` — —

### Lacunas do modelo (pré-check)

- [component_context] 1 componente(s) com responsabilidade/privilégio explícitos.
- [business_context] Sem objetivos de negócio — PASTA/risk-centric degradam.

### Resumo executivo

- Total de ameaças ativas: **21** · Maior score: **25.0**
- Metodologia aplicada: **stride**
- Prioridade imediata:
  - [tampering] Canal do fluxo to_db (score 25.0) em `to_db`
  - [information_disclosure] Canal do fluxo to_db (score 25.0) em `to_db`
  - [spoofing] API (public_api) (score 20.0) em `api`

### Categorias de risco (top)

Bloco curto para leitura humana; a lista completa permanece abaixo (com rastreabilidade no JSON).

#### Abuso de processo / lógica de negócio

- [business_abuse] Autorizacao tecnica sem contexto de negocio (`biz_authorization_without_business_context`) em `—` — score 12.0

#### Técnico clássico (STRIDE)

- [tampering] Canal do fluxo to_db (`eng_flow_to_db_tampering`) em `to_db` — score 25.0
- [information_disclosure] Canal do fluxo to_db (`eng_flow_to_db_information_disclosure`) em `to_db` — score 25.0

### Ameaças sugeridas (harmonizadas)

Visualização priorizada por especificidade (`biz_*`) com redução de redundância semântica.

- **[tampering] Canal do fluxo to_db** (`eng_flow_to_db_tampering`) → alvo `to_db` — score 25.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[information_disclosure] Canal do fluxo to_db** (`eng_flow_to_db_information_disclosure`) → alvo `to_db` — score 25.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, `iso_27001:A.5.14`
- **[spoofing] API (public_api)** (`eng_api_spoofing`) → alvo `api` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, `iso_27001:A.5.16`
- **[elevation_of_privilege] API (public_api)** (`eng_api_elevation_of_privilege`) → alvo `api` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, `iso_27001:A.8.3`
- **[tampering] Atravessa fronteira — http_in** (`eng_flow_http_in_tampering`) → alvo `http_in` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[tampering] Canal do fluxo to_worker** (`eng_flow_to_worker_tampering`) → alvo `to_worker` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[information_disclosure] Canal do fluxo to_worker** (`eng_flow_to_worker_information_disclosure`) → alvo `to_worker` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, `iso_27001:A.5.14`
- **[tampering] API (public_api)** (`eng_api_tampering`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[information_disclosure] API (public_api)** (`eng_api_information_disclosure`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, `iso_27001:A.5.14`
- **[denial_of_service] API (public_api)** (`eng_api_denial_of_service`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`
- **[tampering] Pedidos** (`eng_db_tampering`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[information_disclosure] Pedidos** (`eng_db_information_disclosure`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, `iso_27001:A.5.14`
- **[denial_of_service] Pedidos** (`eng_db_denial_of_service`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`
- **[business_abuse] Autorizacao tecnica sem contexto de negocio** (`biz_authorization_without_business_context`) → alvo `—` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, `iso_27001:A.8.3`
- **[spoofing] Usuário** (`eng_user_spoofing`) → alvo `user` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, `iso_27001:A.5.16`
- **[spoofing] Worker** (`eng_worker_spoofing`) → alvo `worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, `iso_27001:A.5.16`
- **[elevation_of_privilege] Worker** (`eng_worker_elevation_of_privilege`) → alvo `worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, `iso_27001:A.8.3`
- **[repudiation] Usuário** (`eng_user_repudiation`) → alvo `user` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-R`, `owasp_asvs:V7.1.1`, `nist_csf:PR.PS-04`, `nist_csf:DE.CM-03`, `iso_27001:A.8.17`, `iso_27001:A.8.15`
- **[tampering] Worker** (`eng_worker_tampering`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, `iso_27001:A.8.12`
- **[information_disclosure] Worker** (`eng_worker_information_disclosure`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, `iso_27001:A.5.14`
- **[denial_of_service] Worker** (`eng_worker_denial_of_service`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`

### Explicabilidade (resumo)

Motivos estruturados gerados pelo motor (metodologia, achados, risco). Detalhe completo no JSON do resultado.

- **[trust_boundary/trust_boundary]** Fronteira CROSS_BOUNDARY_FLOW — Tráfego entre perímetros exige controlos explícitos; usar este achado para rever segmentação.
- **[threat_heuristic/threat]** [spoofing] Usuário — Heurística identificou spoofing em Usuário (user) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [repudiation] Usuário — Heurística identificou repudiation em Usuário (user) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [spoofing] API (public_api) — Heurística identificou spoofing em API (api) com base no desenho e no motor STRIDE.
- **[risk_score/risk]** Prioridade de risco · eng_api_spoofing — Score ~20 merece prioridade na triagem.
- **[threat_heuristic/threat]** [tampering] API (public_api) — Heurística identificou tampering em API (api) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [information_disclosure] API (public_api) — Heurística identificou information_disclosure em API (api) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [denial_of_service] API (public_api) — Heurística identificou denial_of_service em API (api) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [elevation_of_privilege] API (public_api) — Heurística identificou elevation_of_privilege em API (api) com base no desenho e no motor STRIDE.
- **[risk_score/risk]** Prioridade de risco · eng_api_elevation_of_privilege — Score ~20 merece prioridade na triagem.
- **[threat_heuristic/threat]** [spoofing] Worker — Heurística identificou spoofing em Worker (worker) com base no desenho e no motor STRIDE.
- **[threat_heuristic/threat]** [tampering] Worker — Heurística identificou tampering em Worker (worker) com base no desenho e no motor STRIDE.

… e mais 17 entradas no JSON.

### Próximos passos sugeridos

- Validar os 3 maiores riscos em workshop curto com engenharia e segurança.
- Converter os achados críticos em backlog com owner e prazo.
- Revisar controles de acesso, integridade de fluxo e proteção de dados sensíveis.
