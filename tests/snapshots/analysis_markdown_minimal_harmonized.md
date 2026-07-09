## Análise automática (motor)

- Versão do motor: `0.1.0`
- Metodologia: `stride`
- Avisos estruturais: 0
- Achados de fronteira: 1
- Heurísticas base novas: 21
- Heurísticas base já cobertas: 0
- Ameaças do pack (novas): 0
- Ameaças do pack (já cobertas): 0
- Maior score heurístico (L×I): **20.0**

### Referências a frameworks (agregado)

Contagem de referências `framework:control_id` nas heurísticas (por catálogo canónico):

- **MITRE CAPEC** (`capec`): 21
- **MITRE CWE** (`cwe`): 21
- **ISO/IEC 27001 (Annex A)** (`iso_27001`): 42
- **NIST CSF** (`nist_csf`): 39
- **OWASP ASVS** (`owasp_asvs`): 38
- **OWASP Threat Modeling** (`owasp_tm`): 21

### Consolidação de risco e cockpit executivo

- **Ameaças activas:** 21 · **Score total:** 290.0 · **Média / máx:** 13.81 / 20.0
- **Distribuição por severidade:** `{'high': 14, 'medium': 4, 'critical': 3}`
- **Top ameaças (score):**
  - `eng_api_spoofing` — [spoofing] API (public_api) (score 20.0)
  - `eng_api_elevation_of_privilege` — [elevation_of_privilege] API (public_api) (score 20.0)
  - `eng_flow_http_in_tampering` — [tampering] Atravessa fronteira — http_in (score 20.0)
  - `eng_flow_to_db_tampering` — [tampering] Canal do fluxo to_db (score 16.0)
  - `eng_flow_to_db_information_disclosure` — [information_disclosure] Canal do fluxo to_db (score 16.0)
- **Componentes mais críticos:** `api` (85.0), `worker` (51.0), `db` (45.0), `user` (21.0)
- **Fluxos mais críticos:** `to_db` (32.0), `to_worker` (24.0), `http_in` (20.0)
- **Temas dominantes:** eng: 20; biz: 1
- **Mitigação inicial:**
  - Priorizar `eng_api_spoofing` em `api` (score 20.0).
  - Priorizar `eng_api_elevation_of_privilege` em `api` (score 20.0).
  - Priorizar `eng_flow_http_in_tampering` em `http_in` (score 20.0).
  - Priorizar `eng_flow_to_db_tampering` em `to_db` (score 16.0).
  - Priorizar `eng_flow_to_db_information_disclosure` em `to_db` (score 16.0).
- **Postura:** `elevated` — Postura crítica agregada — tratamento prioritário recomendado.
  - 21 achados heurísticos activos; soma de scores ≈ 290.0.
  - Ordenar backlog pelos `top_threats` e validar com donos de sistema.
  - *Rever:* Rever controlos nas fronteiras com fluxos de maior risco acumulado.
  - *Rever:* Confirmar classificação e retenção nos ativos mais expostos.


### Fluxos entre fronteiras

- Fluxo 'http_in' liga fronteira 'internet' → 'vpc'.

### Qualidade do modelo e metodologia (resumo)

- **Pré-check:** score **62/100** (banda `good`) · confiança nas recomendações: `medium` · fit STRIDE: `strong`.
- **Completude metodológica:** `complete` — —

### Lacunas do modelo (pré-check)

- [component_context] 1 componente(s) com responsabilidade/privilégio explícitos.
- [business_context] Sem objetivos de negócio — PASTA/risk-centric degradam.

### Resumo executivo

- Total de ameaças ativas: **21** · Maior score: **20.0**
- Metodologia aplicada: **stride**
- Prioridade imediata:
  - [spoofing] API (public_api) (score 20.0) em `api`
  - [elevation_of_privilege] API (public_api) (score 20.0) em `api`
  - [tampering] Atravessa fronteira — http_in (score 20.0) em `http_in`

### Categorias de risco (top)

Bloco curto para leitura humana; a lista completa permanece abaixo (com rastreabilidade no JSON).

#### Abuso de processo / lógica de negócio

- [business_abuse] Autorizacao tecnica sem contexto de negocio (`biz_authorization_without_business_context`) em `—` — score 12.0

#### Técnico clássico (STRIDE)

- [spoofing] API (public_api) (`eng_api_spoofing`) em `api` — score 20.0
- [elevation_of_privilege] API (public_api) (`eng_api_elevation_of_privilege`) em `api` — score 20.0

### Ameaças sugeridas (harmonizadas)

Visualização priorizada por especificidade (`biz_*`) com redução de redundância semântica.

- **[spoofing] API (public_api)** (`eng_api_spoofing`) → alvo `api` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `capec:CAPEC-151`, `cwe:CWE-287`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, … (+1)
- **[elevation_of_privilege] API (public_api)** (`eng_api_elevation_of_privilege`) → alvo `api` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `capec:CAPEC-233`, `cwe:CWE-269`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, … (+1)
- **[tampering] Atravessa fronteira — http_in** (`eng_flow_http_in_tampering`) → alvo `http_in` — score 20.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[tampering] Canal do fluxo to_db** (`eng_flow_to_db_tampering`) → alvo `to_db` — score 16.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[information_disclosure] Canal do fluxo to_db** (`eng_flow_to_db_information_disclosure`) → alvo `to_db` — score 16.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `capec:CAPEC-118`, `cwe:CWE-200`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, … (+1)
- **[tampering] API (public_api)** (`eng_api_tampering`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[information_disclosure] API (public_api)** (`eng_api_information_disclosure`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `capec:CAPEC-118`, `cwe:CWE-200`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, … (+1)
- **[denial_of_service] API (public_api)** (`eng_api_denial_of_service`) → alvo `api` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `capec:CAPEC-125`, `cwe:CWE-400`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`
- **[tampering] Pedidos** (`eng_db_tampering`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[information_disclosure] Pedidos** (`eng_db_information_disclosure`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `capec:CAPEC-118`, `cwe:CWE-200`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, … (+1)
- **[denial_of_service] Pedidos** (`eng_db_denial_of_service`) → alvo `db` — score 15.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `capec:CAPEC-125`, `cwe:CWE-400`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`
- **[business_abuse] Autorizacao tecnica sem contexto de negocio** (`biz_authorization_without_business_context`) → alvo `—` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `capec:CAPEC-233`, `cwe:CWE-269`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, … (+1)
- **[spoofing] Usuário** (`eng_user_spoofing`) → alvo `user` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `capec:CAPEC-151`, `cwe:CWE-287`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, … (+1)
- **[spoofing] Worker** (`eng_worker_spoofing`) → alvo `worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-S`, `capec:CAPEC-151`, `cwe:CWE-287`, `owasp_asvs:V2.2.1`, `owasp_asvs:V3.2.1`, `nist_csf:PR.AA-01`, `nist_csf:PR.AA-05`, `iso_27001:A.8.5`, … (+1)
- **[elevation_of_privilege] Worker** (`eng_worker_elevation_of_privilege`) → alvo `worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-E`, `capec:CAPEC-233`, `cwe:CWE-269`, `owasp_asvs:V4.1.1`, `owasp_asvs:V4.2.1`, `nist_csf:PR.AC-01`, `nist_csf:PR.AC-04`, `iso_27001:A.8.2`, … (+1)
- **[tampering] Canal do fluxo to_worker** (`eng_flow_to_worker_tampering`) → alvo `to_worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[information_disclosure] Canal do fluxo to_worker** (`eng_flow_to_worker_information_disclosure`) → alvo `to_worker` — score 12.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `capec:CAPEC-118`, `cwe:CWE-200`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, … (+1)
- **[repudiation] Usuário** (`eng_user_repudiation`) → alvo `user` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-R`, `capec:CAPEC-93`, `cwe:CWE-778`, `owasp_asvs:V7.1.1`, `nist_csf:PR.PS-04`, `nist_csf:DE.CM-03`, `iso_27001:A.8.17`, `iso_27001:A.8.15`
- **[tampering] Worker** (`eng_worker_tampering`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-T`, `capec:CAPEC-184`, `cwe:CWE-345`, `owasp_asvs:V5.1.1`, `owasp_asvs:V14.1.1`, `nist_csf:PR.DS-06`, `nist_csf:PR.PS-01`, `iso_27001:A.8.9`, … (+1)
- **[information_disclosure] Worker** (`eng_worker_information_disclosure`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-I`, `capec:CAPEC-118`, `cwe:CWE-200`, `owasp_asvs:V8.3.1`, `owasp_asvs:V9.1.1`, `nist_csf:PR.DS-01`, `nist_csf:PR.DS-02`, `iso_27001:A.8.11`, … (+1)
- **[denial_of_service] Worker** (`eng_worker_denial_of_service`) → alvo `worker` — score 9.0  
  - Frameworks: `owasp_tm:STRIDE-D`, `capec:CAPEC-125`, `cwe:CWE-400`, `owasp_asvs:V11.1.1`, `nist_csf:PR.IR-01`, `iso_27001:A.8.6`, `iso_27001:A.8.13`

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

… e mais 13 entradas no JSON.

### Próximos passos sugeridos

- Validar os 3 maiores riscos em workshop curto com engenharia e segurança.
- Converter os achados críticos em backlog com owner e prazo.
- Revisar controles de acesso, integridade de fluxo e proteção de dados sensíveis.
