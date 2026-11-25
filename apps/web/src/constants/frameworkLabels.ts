// Um rótulo por framework que o motor emite. Sem entrada, `ThreatsAnalysisCard` cai no id cru
// (`?? r.framework`), e o utilizador via `cwe:79` em minúsculas ao lado de `OWASP ASVS:V5.3.4`.
// `tests/test_p6_ui_framework_labels.py` falha se o motor passar a emitir um framework sem rótulo.
export const FRAMEWORK_LABELS: Record<string, string> = {
  owasp_tm: "OWASP TM",
  owasp_asvs: "OWASP ASVS",
  nist_csf: "NIST CSF",
  iso_27001: "ISO 27001",
  cwe: "CWE",
  capec: "CAPEC",
};

