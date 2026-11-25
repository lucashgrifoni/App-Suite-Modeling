"""
Importação assistida de artefactos reais para rascunhos `ThreatModelDocument`.

Cada importador devolve `ArtifactImportResult` com documento canónico + inferências explícitas.
"""

from otm_artifact_import.helm_import import import_helm_path, import_helm_text
from otm_artifact_import.k8s_import import import_kubernetes_path, import_kubernetes_text, kubernetes_manifest_files
from otm_artifact_import.openapi_import import import_openapi_path, import_openapi_text
from otm_artifact_import.repo_scan import scan_node_express_repo
from otm_artifact_import.terraform_import import import_terraform_path, import_terraform_text, terraform_files
from otm_artifact_import.types import ArtifactImportResult, InferenceRecord

__all__ = [
    "terraform_files",
    "kubernetes_manifest_files",
    "ArtifactImportResult",
    "InferenceRecord",
    "import_helm_path",
    "import_helm_text",
    "import_kubernetes_path",
    "import_kubernetes_text",
    "import_openapi_path",
    "import_openapi_text",
    "import_terraform_path",
    "import_terraform_text",
    "scan_node_express_repo",
]
