"""
Locale do report premium — delega a ``otm_exporters.export_locale``.

Uma única implementação de normalização evita divergência export vs premium.
"""

from __future__ import annotations

from otm_exporters.export_locale import ExportArtifactLocale as PremiumReportLocale
from otm_exporters.export_locale import normalize_export_locale as normalize_premium_locale

__all__ = ["PremiumReportLocale", "normalize_premium_locale"]
