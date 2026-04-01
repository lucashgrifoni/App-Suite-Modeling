"""Enumeradores do modelo canônico v1 (valores estáveis para YAML/JSON)."""

from enum import StrEnum


class StrideCategory(StrEnum):
    SPOOFING = "spoofing"
    TAMPERING = "tampering"
    REPUDIATION = "repudiation"
    INFORMATION_DISCLOSURE = "information_disclosure"
    DENIAL_OF_SERVICE = "denial_of_service"
    ELEVATION_OF_PRIVILEGE = "elevation_of_privilege"


class ThreatModelMethodology(StrEnum):
    """Metodologias principais suportadas pela arquitetura de engines."""

    STRIDE = "stride"
    LINDDUN = "linddun"
    NIST_DATA_CENTRIC = "nist_data_centric"
    OCTAVE_ALLEGRO = "octave_allegro"
    CIA_DIE = "cia_die"
    PASTA = "pasta"
    PLOT4AI = "plot4ai"


class ComponentKind(StrEnum):
    """Elemento no diagrama lógico (DFD + extensões comuns)."""

    PROCESS = "process"
    DATASTORE = "datastore"
    EXTERNAL_ENTITY = "external_entity"
    USER = "user"
    GATEWAY = "gateway"
    QUEUE = "queue"
    OTHER = "other"


class SystemType(StrEnum):
    """Tipo técnico do sistema modelado (para templates e wizard)."""

    WEB_APPLICATION = "web_application"
    API_BACKEND = "api_backend"
    MOBILE_APPLICATION = "mobile_application"
    DESKTOP = "desktop"
    BATCH_DATA_PIPELINE = "batch_data_pipeline"
    IOT_SYSTEM = "iot_system"
    HYBRID = "hybrid"
    OTHER = "other"


class IndustrySector(StrEnum):
    """Domínio / setor de negócio (relatórios, packs, compliance)."""

    GENERIC = "generic"
    SAAS = "saas"
    FINANCE = "finance"
    TELECOM = "telecom"
    TRANSPORT = "transport"
    HEALTHCARE = "healthcare"
    GOVERNMENT = "government"
    RETAIL = "retail"
    CLOUD_NATIVE = "cloud_native"
    OTHER = "other"


class AssetKind(StrEnum):
    """Classificação simples de ativo (sem duplicar GRC pesado)."""

    DATA = "data"
    CREDENTIAL = "credential"
    CRYPTO_KEY = "crypto_key"
    SERVICE = "service"
    HARDWARE = "hardware"
    OTHER = "other"


class TreatmentStatus(StrEnum):
    """Estado de tratamento da ameaça (backlog / workflow)."""

    NEW = "new"
    TRIAGED = "triaged"
    IN_PROGRESS = "in_progress"
    MITIGATED = "mitigated"
    ACCEPTED_RISK = "accepted_risk"
    FALSE_POSITIVE = "false_positive"
    WONT_FIX = "wont_fix"


class MitigationStatus(StrEnum):
    """Estado da mitigação."""

    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    IMPLEMENTED = "implemented"
    VERIFIED = "verified"
    CANCELLED = "cancelled"


class EvidenceKind(StrEnum):
    """Tipo de evidência sugerida (para auditoria / DevSecOps)."""

    LOG_REVIEW = "log_review"
    CONFIG_REVIEW = "config_review"
    PENETRATION_TEST = "penetration_test"
    CODE_REVIEW = "code_review"
    INTERVIEW = "interview"
    AUTOMATED_SCAN = "automated_scan"
    OTHER = "other"
