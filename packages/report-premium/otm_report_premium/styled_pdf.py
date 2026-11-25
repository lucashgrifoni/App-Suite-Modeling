"""The five-section risk report layout. Model data enters as escaped PDF text only."""

from __future__ import annotations

from base64 import b64decode
from collections import Counter
from html import escape
from io import BytesIO
from textwrap import shorten

from otm_core_schema import ThreatModelDocument, TreatmentStatus
from otm_exporters.threat_treatment import treatment_text
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import (
    BaseDocTemplate,
    Flowable,
    Frame,
    HRFlowable,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

from .branding import report_logo_data_uri
from .models import DeclaredThreatTreatment, PremiumReportPayload, TopRiskItem
from .pdf_text import to_pdf_font_text
from .treatment_overview import (
    decision_details,
    decision_sections,
    exposure_overview,
    pending_check,
    treatment_follow_up,
    treatment_overview,
)

_PAGE_W, _PAGE_H = A4
_LEFT = 42
_WIDTH = _PAGE_W - 2 * _LEFT
_INK = "#0B1220"
_DARK = "#16201C"
_BODY = "#263B34"
_MUTED = "#475A53"
_SOFT = "#EAF4EE"
_GREEN = "#0F766E"
_EMERALD = "#30B27F"
_MINT = "#7DFABE"
_RULE = "#CBDAD1"
_WHITE = "#FFFFFF"
_TIER_COLORS = {"P1": ("#A42D35", "#FDEDEF"), "P2": ("#8B4E12", "#FBF0D9"), "P3": ("#62501A", "#F5EDCD")}
_STATUS_COLORS = {
    TreatmentStatus.IN_PROGRESS: ("#265F7C", "#E4F2F7"),
    TreatmentStatus.ACCEPTED_RISK: ("#684D86", "#F0EAF8"),
    TreatmentStatus.MITIGATED: ("#0F766E", "#EAF4EE"),
    TreatmentStatus.TRIAGED: ("#62501A", "#F5EDCD"),
}
_SEVERITY = (
    ("critical", "#AF3840", "Críticas", "Critical"),
    ("high", "#CA6928", "Altas", "High"),
    ("medium", "#D6A12D", "Médias", "Medium"),
    ("low", "#70AE91", "Baixas", "Low"),
    ("info", "#8CA5AD", "Informativas", "Informational"),
)
_EMPTY_STYLE = [
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
]

_NOTE_PANEL = [
    ("BACKGROUND", (0, 0), (-1, -1), HexColor("#F4F7F5")),
    ("LEFTPADDING", (0, 0), (-1, -1), 13),
    ("RIGHTPADDING", (0, 0), (-1, -1), 13),
    ("TOPPADDING", (0, 0), (-1, 0), 10),
    ("TOPPADDING", (0, 1), (-1, 1), 4),
    ("BOTTOMPADDING", (0, 1), (-1, 1), 10),
]


def _safe(value: str) -> str:
    return escape(to_pdf_font_text(value))


def _text(value: str, *, size: float = 10.5, color: str = _BODY, bold: bool = False) -> Paragraph:
    return _markup(_safe(value), size=size, color=color, bold=bold)


def _markup(value: str, *, size: float = 10.5, color: str = _BODY, bold: bool = False) -> Paragraph:
    return Paragraph(
        value,
        ParagraphStyle(
            "RiskReport",
            fontName="Helvetica-Bold" if bold else "Helvetica",
            fontSize=size,
            leading=size * 1.28,
            textColor=HexColor(color),
        ),
    )


def _mono(value: str, *, size: float = 8.4) -> Paragraph:
    return _markup(f'<font name="Courier">{_safe(value)}</font>', size=size, color=_MUTED)


def _tag(label: str, colors: tuple[str, str]) -> str:
    fg, bg = colors
    return f'<span color="{fg}" backColor="{bg}">  {_safe(label)}  </span>'


def _table(
    rows: list,
    widths: list[float],
    commands: list | None = None,
    **options,
) -> Table:
    return Table(rows, colWidths=widths, hAlign="LEFT", style=TableStyle(_EMPTY_STYLE + (commands or [])), **options)


def _line() -> HRFlowable:
    return HRFlowable(width="100%", thickness=0.6, color=HexColor(_RULE), spaceBefore=10, spaceAfter=11)


def _compact(value: str, max_width: float, size: float, font: str = "Helvetica") -> str:
    value = " ".join(to_pdf_font_text(value).split())
    if stringWidth(value, font, size) <= max_width:
        return value
    end = min(len(value), int(max_width * 3 / size))
    while end and stringWidth(value[:end] + "…", font, size) > max_width:
        end -= 1
    return value[:end].rstrip() + "…"


def _draw_rect(
    canvas: Canvas,
    x: float,
    y: float,
    width: float,
    height: float,
    color: str,
    radius: float = 0,
    border: str | None = None,
) -> None:
    canvas.setFillColor(HexColor(color))
    if border:
        canvas.setStrokeColor(HexColor(border))
        canvas.setLineWidth(0.6)
    canvas.roundRect(x, y, width, height, radius, stroke=int(bool(border)), fill=1)


def _draw_label(
    canvas: Canvas, label: str, x: float, y: float, size: float, color: str, *, bold: bool = False, mode: str = "left"
) -> None:
    canvas.setFillColor(HexColor(color))
    canvas.setFont("Helvetica-Bold" if bold else "Helvetica", size)
    draw = {"left": canvas.drawString, "center": canvas.drawCentredString, "right": canvas.drawRightString}[mode]
    draw(x, y, to_pdf_font_text(label))


def _draw_line(canvas: Canvas, x1: float, y1: float, x2: float, y2: float, color: str, width: float = 0.65) -> None:
    canvas.setStrokeColor(HexColor(color))
    canvas.setLineWidth(width)
    canvas.line(x1, y1, x2, y2)


def _load_brand() -> ImageReader | None:
    from PIL import Image

    uri = report_logo_data_uri()
    if not uri:
        return None
    try:
        with Image.open(BytesIO(b64decode(uri.partition(",")[2]))) as source:
            logo = source.convert("RGBA")
        alpha = logo.getchannel("A")
        box = alpha.point(lambda alpha_value: 255 if alpha_value > 24 else 0).getbbox()
        return ImageReader(logo.crop(box)) if box else None
    except (OSError, ValueError):
        return None


class _NumberedCanvas(Canvas):
    def save(self) -> None:
        # One form fills the page count everywhere after layout has established the total.
        self.beginForm("RiskReportPageCount", 0, -3, 25, 11)
        _draw_label(self, f"{self.getPageNumber() - 1:02d}", 0, 0, 8.5, _GREEN)
        self.endForm()
        super().save()


class _Section(Flowable):
    keepWithNext = True

    def __init__(self, anchor: str, display: str) -> None:
        super().__init__()
        self.anchor = anchor
        self.display = display

    def draw(self) -> None:
        pass


class _RiskDocument(BaseDocTemplate):
    section = ""

    def afterFlowable(self, flowable: Flowable) -> None:
        if isinstance(flowable, _Section):
            self.section = flowable.display
            self.canv.bookmarkPage(flowable.anchor)
            self.canv.addOutlineEntry(flowable.display, flowable.anchor)


class _StackedBar(Flowable):
    def __init__(self, segments: list[tuple[float, str]], *, width: float = _WIDTH, height: float = 13) -> None:
        super().__init__()
        self.width = width
        self.height = height
        self.segments = segments

    def draw(self) -> None:
        offset = 0.0
        for magnitude, color in self.segments:
            length = magnitude * self.width
            self.canv.setFillColor(HexColor(color))
            self.canv.rect(offset, 0, length, self.height, stroke=0, fill=1)
            offset += length


class _ArchitectureDiagram(Flowable):
    """Draw only model edges. Repeated boundary groups show the boundary of each displayed node."""

    def __init__(
        self, nodes: list[tuple[str, str, str | None]], protocols: list[str], boundaries: dict[str, str]
    ) -> None:
        super().__init__()
        self.nodes = nodes
        self.boundaries = boundaries
        self.protocols = protocols
        self.width, self.height = _WIDTH, 129

    def draw(self) -> None:
        canvas = self.canv
        step = self.width / len(self.nodes)
        centers = [step * (i + 0.5) for i in range(len(self.nodes))]
        node_width = min(78, step * 0.57)
        y = 59
        groups: list[tuple[int, int, str | None]] = []
        for pos, (_, _, boundary) in enumerate(self.nodes):
            if groups and boundary == groups[-1][2]:
                start, _, _ = groups[-1]
                groups[-1] = (start, pos, boundary)
            else:
                groups.append((pos, pos, boundary))
        for i, (start, end, boundary_id) in enumerate(groups):
            x = start * step + 1
            w = (end - start + 1) * step - 5
            shade = "#F5F7F6" if i == 0 else "#F1F9F4"
            _draw_rect(canvas, x, 1, w, 127, shade, 7, "#A6CBBA" if boundary_id else _RULE)
            if boundary_id:
                label = _compact(self.boundaries.get(boundary_id, boundary_id), w - 24, 9.5, "Helvetica-Bold")
                _draw_label(canvas, label, x + 12, 106, 9.5, _GREEN, bold=True)
        for pos, (ident, label, _) in enumerate(self.nodes):
            cx = centers[pos]
            _draw_rect(canvas, cx - node_width / 2, y - 17, node_width, 34, _WHITE, 6, "#8DAA9B")
            _draw_label(
                canvas,
                _compact(label, node_width - 8, 10.2, "Helvetica-Bold"),
                cx,
                y - 3,
                10.2,
                _INK,
                bold=True,
                mode="center",
            )
            _draw_label(canvas, _compact(ident, step - 14, 8), cx, y - 36, 8, _MUTED, mode="center")
        for pos, protocol in enumerate(self.protocols):
            x1, x2 = centers[pos] + node_width / 2, centers[pos + 1] - node_width / 2
            _draw_line(canvas, x1 + 1, y, x2 - 2, y, _GREEN, 1.15)
            _draw_line(canvas, x2 - 6, y - 3, x2 - 2, y, _GREEN, 1.15)
            _draw_line(canvas, x2 - 6, y + 3, x2 - 2, y, _GREEN, 1.15)
            _draw_label(canvas, _compact(protocol, x2 - x1, 8), (x1 + x2) / 2, y + 23, 8, _MUTED, mode="center")


_RISK_NAMES = {
    "spoofing": "Falsificação de identidade",
    "tampering": "Alteração de dados",
    "repudiation": "Repúdio",
    "information_disclosure": "Exposição de dados",
    "denial_of_service": "Indisponibilidade",
    "elevation_of_privilege": "Elevação de privilégio",
}
_CHECKS = {
    TreatmentStatus.NEW: (
        "Avaliar a ameaça e registrar a decisão de tratamento.",
        "Assess the threat and record the treatment decision.",
    ),
    TreatmentStatus.TRIAGED: (
        "Confirmar a avaliação e registrar a ação de tratamento.",
        "Confirm the assessment and record the treatment action.",
    ),
    TreatmentStatus.IN_PROGRESS: (
        "Reunir evidência de validação da medida em andamento.",
        "Collect evidence that validates the treatment in progress.",
    ),
    TreatmentStatus.MITIGATED: (
        "Conferir a evidência da mitigação e revisar o risco residual.",
        "Check the mitigation evidence and review the residual risk.",
    ),
    TreatmentStatus.ACCEPTED_RISK: (
        "Confirmar se as condições descritas no aceite continuam válidas.",
        "Confirm that the conditions recorded in the acceptance still apply.",
    ),
    TreatmentStatus.FALSE_POSITIVE: (
        "Revalidar a classificação se a arquitetura ou as condições mudarem.",
        "Revalidate the classification if the architecture or conditions change.",
    ),
    TreatmentStatus.WONT_FIX: (
        "Reavaliar a justificativa se a exposição ou o impacto mudarem.",
        "Review the rationale if the exposure or impact changes.",
    ),
}


class _Report:
    def __init__(self, payload: PremiumReportPayload, doc: ThreatModelDocument, *, analysis_generated: bool) -> None:
        self.payload = payload
        self.model = doc
        self.generated = analysis_generated
        self.pt = payload.locale == "pt-BR"
        self.copy = treatment_text(payload.locale)
        self.ranks = payload.top_risks
        self.by_rank = {risk.threat_id: risk for risk in self.ranks}
        self.decisions = {decision.id: decision for decision in payload.declared_treatments}
        self.ordered_decisions = sorted(
            self.decisions.values(),
            key=lambda decision: self.by_rank[decision.id].rank if decision.id in self.by_rank else len(self.ranks) + 1,
        )
        self.document_threats = {threat.id: threat for threat in doc.threats}
        self.components = {component.id: component for component in doc.components}
        self.boundaries = {boundary.id: boundary.name for boundary in doc.trust_boundaries}
        severity = payload.executive_summary.severity_distribution
        self.total = payload.executive_summary.threat_count
        self.scored = sum(severity.values())
        known = {band: (color, local if self.pt else english) for band, color, local, english in _SEVERITY}
        self.severity = [
            (known.get(band, ("#829291", band)), severity[band])
            for band in dict.fromkeys([*known, *severity])
            if severity.get(band, 0) > 0
        ]
        self.title, _, self.subtitle = payload.cover.title.partition(" — ")
        self.logo = _load_brand()

    def choose(self, pt: str, en: str) -> str:
        return pt if self.pt else en

    def threat_title(self, title: str) -> str:
        category, delimiter, context = title.partition("] ")
        translation = _RISK_NAMES.get(category.removeprefix("["))
        if self.pt and delimiter and translation:
            return f"{translation} · {context}"
        return title

    def state(self, ident: str) -> str:
        decision = self.decisions.get(ident)
        return self.copy.statuses[decision.treatment_status] if decision else self.choose("Sem decisão", "No decision")

    def suggestion(self, decision: DeclaredThreatTreatment) -> str:
        if decision.destination not in (None, "action"):
            return treatment_follow_up(decision, self.payload.locale)
        return self.choose(*_CHECKS[decision.treatment_status])

    def action_decisions(self, limit: int) -> list[DeclaredThreatTreatment]:
        return [d for d in self.ordered_decisions if d.destination not in ("review_accepted", "history")][:limit]

    def opening(
        self,
        key: str,
        label: str,
        title: str,
        *,
        size: float = 32,
        subtitle: str = "",
    ) -> list[Flowable]:
        items: list[Flowable] = [
            _Section(key, label),
            _text(label.upper(), size=8.4, color=_GREEN, bold=True),
            Spacer(1, 10),
            _text(title, size=size, color=_INK, bold=True),
            Spacer(1, 8),
        ]
        if subtitle:
            items.extend([_text(subtitle, size=11, color=_MUTED), Spacer(1, 12)])
        return items

    def _header(self, canvas: Canvas, doc: _RiskDocument) -> None:
        canvas.saveState()
        if self.logo:
            iw, ih = self.logo.getSize()
            scale = min(114 / iw, 36 / ih)
            canvas.drawImage(self.logo, _LEFT, _PAGE_H - 40 - ih * scale / 2, iw * scale, ih * scale, mask="auto")
        else:
            _draw_label(canvas, "App Suite Modeling", _LEFT, _PAGE_H - 41, 12, _INK, bold=True)
        right = _PAGE_W - _LEFT
        _draw_label(
            canvas,
            self.choose("RELATÓRIO DE RISCOS", "RISK REPORT"),
            right,
            _PAGE_H - 36,
            8.3,
            _GREEN,
            bold=True,
            mode="right",
        )
        date = self.payload.cover.analysis_date_iso
        label = self.choose("Gerado em", "Generated on")
        _draw_label(canvas, f"{label}  /  {date}", right, _PAGE_H - 51, 8.7, _MUTED, mode="right")
        _draw_line(canvas, _LEFT, _PAGE_H - 67, right, _PAGE_H - 67, _RULE)
        canvas.restoreState()

    def _footer(self, canvas: Canvas, doc: _RiskDocument) -> None:
        canvas.saveState()
        right = _PAGE_W - _LEFT
        _draw_line(canvas, _LEFT, 53, right, 53, _RULE)
        text = f"{self.title}  /  {doc.section}"
        _draw_label(canvas, _compact(text, _WIDTH - 78, 8.7), _LEFT, 33, 8.7, _MUTED)
        _draw_label(canvas, f"{doc.page:02d} /", right - 20, 33, 8.5, _GREEN, mode="right")
        canvas.translate(right - 16, 33)
        canvas.doForm("RiskReportPageCount")
        canvas.restoreState()

    def _hero(self, peak: TopRiskItem) -> Table:
        decision = self.decisions.get(peak.threat_id)
        badges = (
            _tag(peak.priority_tier, _TIER_COLORS[peak.priority_tier])
            + "  "
            + _tag(
                self.state(peak.threat_id),
                ("#D4EFEE", "#26554F"),
            )
        )
        head = _table(
            [
                [
                    _text(
                        self.choose("PRIMEIRA PRIORIDADE DE AÇÃO", "TOP ACTION PRIORITY"),
                        size=8.4,
                        color=_MINT,
                        bold=True,
                    ),
                    _markup(badges, size=8.5),
                ]
            ],
            [_WIDTH - 206, 168],
        )
        if decision and decision.treatment_notes and decision.treatment_notes.strip():
            display = shorten(decision.treatment_notes, width=250, placeholder="…")
        else:
            display = shorten(peak.recommended_action, width=250, placeholder="…")
        if decision:
            link = self.choose("Decisão registrada", "Recorded decision")
            foot = _markup(f'<link href="#decisions">{link}</link>', size=8.8, color=_MINT, bold=True)
        else:
            foot = _text(peak.threat_id, size=8.7, color=_MINT)
        body = [
            [head],
            [_text(self.threat_title(peak.title), size=19.5, color=_WHITE, bold=True)],
            [_text(display, size=10.7, color="#DCEAE1")],
            [foot],
        ]
        return _table(
            body,
            [_WIDTH],
            [
                ("BACKGROUND", (0, 0), (-1, -1), HexColor(_DARK)),
                ("LINEBEFORE", (0, 0), (0, -1), 3, HexColor(_EMERALD)),
                ("LEFTPADDING", (0, 0), (-1, -1), 18),
                ("RIGHTPADDING", (0, 0), (-1, -1), 18),
                ("TOPPADDING", (0, 0), (-1, 0), 15),
                ("TOPPADDING", (0, 1), (-1, -1), 8),
                ("BOTTOMPADDING", (0, -1), (-1, -1), 14),
            ],
            cornerRadii=[9] * 4,
            splitInRow=1,
        )

    def _metrics(self) -> Table:
        n = len(self.decisions)
        active = self.payload.exposure_count if self.payload.exposure_count is not None else self.total
        scored_detail = self.choose("Base da distribuição abaixo", "Basis of the distribution below")
        unscored_detail = self.choose("Ameaças fora do ranking", "Threats outside the ranking")
        if self.payload.exposure_count is not None:
            scored_detail = unscored_detail = self.choose("Da exposição ativa", "In active exposure")
        counts = [
            (
                self.total,
                self.choose("ameaças no total", "total threats"),
                self.choose(
                    f"{n} declaradas + {self.total - n} sugestões", f"{n} declared + {self.total - n} suggestions"
                ),
            ),
            (self.scored, self.choose("com pontuação", "scored"), scored_detail),
            (active - self.scored, self.choose("sem pontuação", "unscored"), unscored_detail),
        ]
        cells = [
            [
                _text(str(count), size=33, color=_INK, bold=True),
                _text(label, size=10.8, bold=True),
                _text(detail, size=8.5, color=_MUTED),
            ]
            for count, label, detail in counts
        ]
        return _table(
            [cells],
            [_WIDTH / 3] * 3,
            [
                ("LINEBEFORE", (1, 0), (2, 0), 0.6, HexColor(_RULE)),
                ("LEFTPADDING", (1, 0), (-1, -1), 13),
            ],
        )

    def _severity_chart(self) -> list[Flowable]:
        title = self.choose("Severidade das ameaças pontuadas", "Scored threats by severity")
        if self.payload.exposure_count is not None:
            title = self.choose("Severidade da exposição ativa", "Active exposure by severity")
        result: list[Flowable] = [_text(title, size=16, color=_INK, bold=True), Spacer(1, 8)]
        if not self.severity:
            result.append(_text(self.choose("Nenhuma ameaça pontuada.", "No scored threats.")))
            return result
        segments = [(count / self.scored, shade) for (shade, _), count in self.severity]
        legend = [
            _markup(f'<font color="{shade}">•</font>  {_safe(str(count))} {_safe(label.lower())}', size=10.1, bold=True)
            for (shade, label), count in self.severity
        ]
        result.extend([_StackedBar(segments), Spacer(1, 12), _table([legend], [_WIDTH / len(legend)] * len(legend))])
        return result

    def cover(self) -> list[Flowable]:
        label = self.choose("Resumo executivo", "Executive summary")
        story = self.opening("summary", label, self.title, size=42)
        story.extend(
            [
                _text(
                    self.subtitle or self.choose("Revisão de arquitetura", "Architecture review"), size=16, color=_MUTED
                ),
                Spacer(1, 8),
                _text(
                    f"{self.payload.cover.analysis_date_iso}  /  {self.payload.cover.primary_methodology.upper()}  /  "
                    f"{self.payload.cover.system_type}",
                    size=9.5,
                    color=_MUTED,
                ),
                Spacer(1, 20),
            ]
        )
        if self.ranks:
            story.extend([self._hero(self.ranks[0]), Spacer(1, 21)])
        story.append(self._metrics())
        if exposure := exposure_overview(self.payload):
            story.extend([Spacer(1, 9), _text(exposure, size=9.4, color=_BODY, bold=True)])
        if overview := treatment_overview(self.payload):
            heading = self.choose("Tratamento", "Treatment")
            story.extend(
                [
                    Spacer(1, 9),
                    _markup(
                        f"<b>{heading}</b> — {_safe(overview)}",
                        size=9.4,
                        color=_BODY,
                    ),
                ]
            )
        story.extend([Spacer(1, 21), *self._severity_chart(), Spacer(1, 8), _line()])
        next_checks = [(self.threat_title(d.title), self.suggestion(d)) for d in self.action_decisions(2)]
        if not next_checks:
            next_checks = [(self.threat_title(r.title), shorten(r.recommended_action, 210)) for r in self.ranks[:2]]
        if next_checks:
            next_label = self.choose("Para a próxima revisão", "For the next review")
            story.append(_text(next_label, size=18, color=_INK, bold=True))
        for name, check in next_checks:
            name = shorten(name, width=110, placeholder="…")
            story.extend(
                [
                    Spacer(1, 8),
                    _markup(
                        f'<font color="{_GREEN}">•</font>  <b>{_safe(name)}</b> — {_safe(check)}',
                        size=10.1,
                    ),
                ]
            )
        if self.generated:
            story.extend(
                [
                    Spacer(1, 9),
                    _text(
                        self.choose(
                            "Análise gerada na exportação a partir do modelo fornecido.",
                            "Analysis generated at export from the supplied model.",
                        ),
                        size=8.6,
                        color=_MUTED,
                    ),
                ]
            )
        story.extend(
            [
                Spacer(1, 15),
                _markup(
                    self.choose(
                        '<link href="#ranking">Prioridades</link>      '
                        '<link href="#decisions">Decisões</link>      '
                        '<link href="#architecture">Arquitetura</link>      '
                        '<link href="#review">Próxima revisão</link>',
                        '<link href="#ranking">Priorities</link>      '
                        '<link href="#decisions">Decisions</link>      '
                        '<link href="#architecture">Architecture</link>      '
                        '<link href="#review">Next review</link>',
                    ),
                    size=9.5,
                    color=_GREEN,
                    bold=True,
                ),
            ]
        )
        return story

    def ranking(self) -> list[Flowable]:
        title = (
            self.choose("Dez riscos prioritários", "Ten prioritized risks")
            if len(self.ranks) == 10
            else self.choose("Riscos prioritários", "Prioritized risks")
        )
        rankable = self.payload.ranking_candidate_count
        if rankable is None:
            rankable = self.scored
        story = self.opening(
            "ranking",
            self.choose("Priorização", "Prioritization"),
            title,
            subtitle=self.choose(
                f"{len(self.ranks)} posições entre {rankable} ameaças pontuadas com ação pendente.",
                f"{len(self.ranks)} positions among {rankable} scored threats with pending action.",
            ),
        )
        labels = self.choose(
            "#|Ameaça e identificador|Faixa|Risco|Índice|Tratamento",
            "#|Threat and identifier|Tier|Risk|Index|Treatment",
        ).split("|")
        rows: list = [[_text(label, size=8.5, bold=True, color=_MUTED) for label in labels]]
        for risk in self.ranks:
            risk_heading = [
                _text(self.threat_title(risk.title), size=10.4, color=_INK, bold=True),
                Spacer(1, 2),
                _mono(risk.threat_id),
            ]
            score = f"{risk.severity_score:g}" if risk.severity_score is not None else "—"
            index = f"{risk.composite_score:.2f}"
            state = self.state(risk.threat_id)
            decision = self.decisions.get(risk.threat_id)
            if pending := pending_check(decision, self.payload.locale):
                state = f"{state} · {pending}"
            status = (
                _markup(f'<link href="#decisions">{_safe(state)}</link>', size=8.7, color=_GREEN, bold=True)
                if decision
                else _text(state, size=8.7, color=_MUTED)
            )
            rows.append(
                [
                    _mono(f"{risk.rank:02d}"),
                    risk_heading,
                    _markup(
                        _tag(risk.priority_tier, _TIER_COLORS[risk.priority_tier]),
                        size=8.3,
                        bold=True,
                    ),
                    _text(score, size=10.2, bold=True),
                    _mono(index.replace(".", ",") if self.pt else index),
                    status,
                ]
            )
        if self.ranks:
            story.append(
                _table(
                    rows,
                    [27, _WIDTH - 251, 42, 39, 46, 97],
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), HexColor(_SOFT)),
                        ("BACKGROUND", (0, 1), (-1, 1), HexColor("#F5FAF7")),
                        ("LINEBEFORE", (0, 1), (0, 1), 2, HexColor(_EMERALD)),
                        ("LINEBELOW", (0, 1), (-1, -1), 0.45, HexColor(_RULE)),
                        ("LEFTPADDING", (0, 0), (-1, -1), 6),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                        ("TOPPADDING", (0, 0), (-1, -1), 7),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ],
                    repeatRows=1,
                    splitInRow=1,
                )
            )
        else:
            story.append(_text(self.choose("Nenhuma ação com pontuação.", "No scored action items.")))
        story.extend(
            [
                Spacer(1, 20),
                _text(self.choose("Como ler o ranking", "How to read the ranking"), size=14, bold=True, color=_INK),
                Spacer(1, 7),
                _text(
                    self.choose(
                        "Risco é probabilidade × impacto. O índice combina risco, exposição e esforço estimado. "
                        "As faixas P1 a P3 seguem a posição no ranking. "
                        "“Sem decisão” indica uma sugestão sem tratamento registrado.",
                        "Risk is likelihood × impact. The index combines risk, exposure, and estimated effort. "
                        "Tiers P1 to P3 follow rank. “No decision” identifies a suggestion without recorded treatment.",
                    ),
                    size=10,
                ),
            ]
        )
        return story

    def decision_card(self, decision: DeclaredThreatTreatment) -> Table:
        tag = _tag(self.state(decision.id), _STATUS_COLORS.get(decision.treatment_status, (_BODY, "#EFF3F0")))
        threat = self.document_threats.get(decision.id)
        rank = self.by_rank.get(decision.id)
        score = self.choose("Sem pontuação", "Unscored")
        if threat and threat.risk:
            value = threat.risk.likelihood * threat.risk.impact
            points = self.choose("pontos", "points")
            score = f"{rank.priority_tier} / {value} {points}" if rank else f"{value} {points}"
        body_width = _WIDTH - 32
        heading = _table(
            [
                [_text(self.threat_title(decision.title), size=14.4, color=_INK, bold=True), _markup(tag, size=8.3)],
                [_mono(decision.id, size=8.8), _text(score, size=8.5, color=_MUTED)],
            ],
            [body_width - 112, 112],
            [("BOTTOMPADDING", (0, 0), (-1, 0), 5)],
        )
        rationale = decision.treatment_notes
        if rationale and rationale.strip():
            note = _markup("<br/>".join(_safe(line) for line in rationale.strip().splitlines()), size=10.6, color=_INK)
        else:
            note = _text(self.copy.missing_rationale, size=10.6, color=_INK)
        check_label = (
            self.choose("Verificação sugerida", "Suggested verification")
            if decision.destination is None
            else self.choose("Encaminhamento", "Follow-up")
        )
        details = [self.suggestion(decision), *decision_details(decision, self.payload.locale)[1:]]
        check = _table(
            [
                [
                    _text(check_label, size=8.8, color=_GREEN, bold=True),
                    [_text(detail, size=9.6) for detail in details],
                ]
            ],
            [105, body_width - 105],
        )
        return _table(
            [
                [heading],
                [_text(self.copy.rationale.upper(), size=8.2, color=_GREEN, bold=True)],
                [note],
                [check],
            ],
            [_WIDTH],
            [
                ("BOX", (0, 0), (-1, -1), 0.6, HexColor(_RULE)),
                ("LINEABOVE", (0, -1), (-1, -1), 0.45, HexColor(_RULE)),
                ("LEFTPADDING", (0, 0), (-1, -1), 16),
                ("RIGHTPADDING", (0, 0), (-1, -1), 16),
                ("TOPPADDING", (0, 0), (-1, 0), 15),
                ("TOPPADDING", (0, 1), (-1, 1), 11),
                ("TOPPADDING", (0, 2), (-1, 2), 5),
                ("BOTTOMPADDING", (0, 2), (-1, 2), 12),
                ("TOPPADDING", (0, 3), (-1, 3), 11),
                ("BOTTOMPADDING", (0, 3), (-1, 3), 12),
                ("NOSPLIT", (0, 0), (-1, 1)),
            ],
            cornerRadii=[7] * 4,
            splitInRow=1,
        )

    def treatment(self) -> list[Flowable]:
        n = len(self.ordered_decisions)
        noted = sum(bool((d.treatment_notes or "").strip()) for d in self.ordered_decisions)
        story = self.opening(
            "decisions",
            self.choose("Tratamento de riscos", "Risk treatment"),
            self.choose("Decisões de tratamento", "Declared threat treatment"),
            subtitle=self.choose(
                f"Ameaças declaradas: {n}. Registros com justificativa: {noted}.",
                f"Declared threats: {n}. Records with a rationale: {noted}.",
            ),
        )
        if not n:
            story.append(_text(self.copy.no_threats))
        for heading, decisions in decision_sections(self.ordered_decisions, self.payload.locale):
            if heading and decisions:
                paragraph = _text(heading, size=16, color=_INK, bold=True)
                paragraph.keepWithNext = True
                paragraph.spaceAfter = 8
                story.append(paragraph)
            for decision in decisions:
                story.extend([self.decision_card(decision), Spacer(1, 14)])
        if any(decision.treatment_status == TreatmentStatus.NEW for decision in self.ordered_decisions):
            story.append(
                _text(
                    self.choose(
                        "Nova é o estado inicial do modelo quando o tratamento ainda não foi preenchido.",
                        "New is the model’s initial status when treatment has not been recorded.",
                    ),
                    size=9.2,
                    color=_MUTED,
                )
            )
        return story

    def _node(self, ident: str) -> tuple[str, str, str | None]:
        component = self.components.get(ident)
        return (ident, component.name, component.in_trust_boundary) if component else (ident, ident, None)

    def _protocol(self, protocol: str | None) -> str:
        if protocol == "internal" and self.pt:
            return "Interno"
        return protocol or self.choose("Protocolo indefinido", "Protocol unspecified")

    def _diagrams(self) -> list[Flowable]:
        flows = self.model.data_flows[:15]
        # A simple path, in graph order. For branches and cycles, use a diagram per actual edge.
        if 0 < len(flows) <= 5:
            outgoing = {flow.from_component: flow for flow in flows}
            incoming = Counter(flow.to_component for flow in flows)
            roots = outgoing.keys() - incoming.keys()
            if len(outgoing) == len(incoming) == len(flows) and len(roots) == 1:
                ident = next(iter(roots))
                nodes = [self._node(ident)]
                protocols = []
                for _ in range(len(flows)):
                    flow = outgoing.get(ident)
                    if flow is None:
                        break
                    ident = flow.to_component
                    nodes.append(self._node(ident))
                    protocols.append(self._protocol(flow.protocol))
                if len(protocols) == len(flows):
                    return [_ArchitectureDiagram(nodes, protocols, self.boundaries)]
        if not flows:
            return [_text(self.choose("Modelo sem fluxos declarados.", "The model has no declared flows."))]
        diagrams: list[Flowable] = []
        for flow in flows:
            diagrams.extend(
                [
                    _ArchitectureDiagram(
                        [self._node(flow.from_component), self._node(flow.to_component)],
                        [self._protocol(flow.protocol)],
                        self.boundaries,
                    ),
                    Spacer(1, 6),
                ]
            )
        return diagrams

    def _flow_observations(self) -> Table:
        states = (
            {True: "declarada", False: "declarada como ausente", None: "sem informação"}
            if self.pt
            else {True: "declared", False: "declared absent", None: "unspecified"}
        )
        rows = []
        for flow in self.model.data_flows[:15]:
            source = self._node(flow.from_component)[1]
            target = self._node(flow.to_component)[1]
            direction = self.choose("para", "to")
            title = [
                _text(f"{source} {direction} {target}", size=10.7, color=_INK, bold=True),
                Spacer(1, 3),
                _mono(flow.id),
            ]
            states_text = self.choose(
                f"Autenticação: {states[flow.authenticated]} · Criptografia: {states[flow.encrypted]}.",
                f"Authentication: {states[flow.authenticated]} · Encryption: {states[flow.encrypted]}.",
            )
            rows.append([title, _text(f"{self._protocol(flow.protocol)}. {states_text}", size=10.2)])
        return _table(
            rows,
            [156, _WIDTH - 156],
            [
                ("LINEABOVE", (0, 0), (-1, -1), 0.5, HexColor(_RULE)),
                ("RIGHTPADDING", (0, 0), (0, -1), 12),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ],
            splitInRow=1,
        )

    def architecture(self) -> list[Flowable]:
        title = self.choose("Arquitetura do modelo", "Model architecture")
        story = self.opening(
            "architecture",
            self.choose("Contexto técnico", "Technical context"),
            title,
            subtitle=self.model.metadata.summary or "",
        )
        graph_title = self.choose("Fronteiras de confiança e sentido dos fluxos", "Trust boundaries and flow direction")
        story.extend([Spacer(1, 12), _text(graph_title.upper(), size=8.4, bold=True, color=_GREEN), Spacer(1, 10)])
        story.extend(self._diagrams())
        story.extend([Spacer(1, 9), _text(self.payload.architecture.narrative, size=9.6, color=_MUTED)])
        if len(self.model.data_flows) > 15:
            flow_count = len(self.model.data_flows)
            story.extend(
                [
                    Spacer(1, 5),
                    _text(
                        self.choose(
                            f"Exibindo 15 de {flow_count} fluxos. Use a exportação do modelo para consultar todos.",
                            f"Showing 15 of {flow_count} flows. Export the model to see all flows.",
                        ),
                        size=9,
                        color=_MUTED,
                    ),
                ]
            )
        if self.model.data_flows:
            story.extend(
                [
                    Spacer(1, 28),
                    _text(
                        self.choose("O que está documentado", "What the model records"), size=19, color=_INK, bold=True
                    ),
                    Spacer(1, 12),
                    self._flow_observations(),
                ]
            )
        if self.payload.architecture.trust_boundaries:
            bounds = ", ".join(self.payload.architecture.trust_boundaries)
            caption = self.choose("Fronteiras modeladas", "Modeled boundaries")
            story.extend([Spacer(1, 12), _text(f"{caption} — {bounds}", size=9.6, color=_MUTED)])
        if self.model.data_flows:
            message = self.choose(
                "Confronte os controles declarados com a configuração do ambiente. Priorize os fluxos "
                "com autenticação ou criptografia sem informação.",
                "Check declared controls against the environment configuration. Start with flows where "
                "authentication or encryption is unspecified.",
            )
            story.extend(
                [
                    Spacer(1, 24),
                    _table(
                        [
                            [
                                _text(
                                    self.choose("USO NA REVISÃO", "USE IN THE REVIEW"),
                                    size=8.3,
                                    color=_GREEN,
                                    bold=True,
                                )
                            ],
                            [_text(message, size=9.8)],
                        ],
                        [_WIDTH],
                        _NOTE_PANEL,
                        cornerRadii=[5] * 4,
                    ),
                ]
            )
        return story

    def _root_causes(self) -> list[Flowable]:
        groups = self.payload.root_cause_groups
        if not groups:
            return []
        largest = max(1, max(group.threat_count for group in groups))
        total = sum(group.threat_count for group in groups)
        rows = [
            [
                _text(group.display_name, size=9.7),
                _StackedBar(
                    [(group.threat_count / largest, _EMERALD), (1 - group.threat_count / largest, "#EFF3F0")],
                    width=200,
                    height=6,
                ),
                _text(str(group.threat_count), size=10.2, bold=True, color=_INK),
            ]
            for group in groups
        ]
        name = self.choose("Causas agrupadas pelo motor", "Root causes grouped by the engine")
        subtitle = self.choose(
            f"Distribuição de {total} itens de remediação por causa sugerida.",
            f"Distribution of {total} remediation items by suggested cause.",
        )
        return [
            Spacer(1, 21),
            _text(name, size=18, color=_INK, bold=True),
            Spacer(1, 8),
            _text(subtitle, size=10.2, color=_MUTED),
            Spacer(1, 11),
            _table(
                rows,
                [_WIDTH - 238, 218, 20],
                [
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (0, -1), 8),
                ],
                splitInRow=1,
            ),
        ]

    def review(self) -> list[Flowable]:
        story = self.opening(
            "review",
            self.choose("Revisão técnica", "Technical review"),
            self.choose("Próxima revisão", "Next review"),
            subtitle=self.choose(
                "Verificações sugeridas para documentar o tratamento e reunir evidências sobre os controles.",
                "Suggested checks for documenting decisions and gathering evidence about controls.",
            ),
        )
        label = self.choose("O que verificar e qual evidência buscar", "What to check and what evidence to look for")
        story.extend([_text(label.upper(), size=8.4, bold=True, color=_GREEN), Spacer(1, 10)])
        suggestions = [(self.threat_title(d.title), self.suggestion(d)) for d in self.action_decisions(3)]
        if not suggestions:
            suggestions = [(self.threat_title(risk.title), risk.recommended_action) for risk in self.ranks[:3]]
        if suggestions:
            story.append(
                _table(
                    [
                        [_text(name, size=10.8, color=_INK, bold=True), _text(check, size=10.3)]
                        for name, check in suggestions
                    ],
                    [158, _WIDTH - 158],
                    [
                        ("LINEABOVE", (0, 0), (-1, -1), 0.6, HexColor(_RULE)),
                        ("RIGHTPADDING", (0, 0), (0, -1), 12),
                        ("TOPPADDING", (0, 0), (-1, -1), 12),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
                    ],
                    splitInRow=1,
                )
            )
        else:
            story.append(
                _text(
                    self.choose(
                        "Revise o escopo do modelo na próxima análise.",
                        "Review the model scope during the next analysis.",
                    )
                )
            )
        story.extend(self._root_causes())
        story.extend(
            [
                Spacer(1, 19),
                _table(
                    [
                        [_text(self.choose("ORIGEM DA ANÁLISE", "ANALYSIS SOURCE"), size=8.3, color=_GREEN, bold=True)],
                        [
                            _text(
                                self.choose(
                                    f"App Suite Modeling {self.payload.cover.app_suite_version} · Esquema do modelo "
                                    f"{self.payload.cover.schema_version}. "
                                    "A confirmação dos controles depende de evidência do ambiente.",
                                    f"App Suite Modeling {self.payload.cover.app_suite_version} · Model schema "
                                    f"{self.payload.cover.schema_version}. "
                                    "Verifying controls requires evidence from the environment.",
                                ),
                                size=9.6,
                            )
                        ],
                    ],
                    [_WIDTH],
                    _NOTE_PANEL,
                    cornerRadii=[5] * 4,
                ),
            ]
        )
        return story

    def comparison(self) -> list[Flowable]:
        baseline = self.payload.baseline_diff
        if not baseline or not baseline.has_baseline:
            return []
        story = self.opening(
            "comparison",
            self.choose("Comparação", "Comparison"),
            self.choose(
                "Comparação com a análise anterior",
                "Baseline comparison",
            ),
            subtitle=baseline.narrative,
        )
        lists = [
            (self.choose("Ameaças adicionadas", "Threats added"), baseline.threats_added[:20]),
            (self.choose("Ameaças removidas", "Threats removed"), baseline.threats_removed[:20]),
            (self.choose("Ameaças modificadas", "Threats modified"), baseline.threats_modified[:20]),
            (self.choose("Observações", "Analysis observations"), baseline.semantic_insights_from_analysis[:10]),
            (self.choose("Melhorias", "Improvements"), baseline.semantic_improved[:8]),
            (self.choose("Pontos de atenção", "Needs attention"), baseline.semantic_worsened[:8]),
            (self.choose("Impacto no risco", "Risk impact"), baseline.semantic_risk_impact[:6]),
        ]
        for name, entries in lists:
            if entries:
                story.extend([Spacer(1, 8), _text(name, size=12, color=_INK, bold=True), Spacer(1, 4)])
                story.extend(_text(f"• {entry}", size=10) for entry in entries)
        return [PageBreak(), *story]

    def build(self) -> bytes:
        result = BytesIO()
        report = _RiskDocument(
            result,
            pagesize=A4,
            title=to_pdf_font_text(self.payload.cover.title),
            author="App Suite Modeling",
            allowSplitting=True,
        )
        frame = Frame(_LEFT, 64, _WIDTH, _PAGE_H - 158, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
        report.addPageTemplates(
            PageTemplate(id="risk-report", frames=[frame], onPage=self._header, onPageEnd=self._footer)
        )
        report.build(
            [
                *self.cover(),
                PageBreak(),
                *self.ranking(),
                PageBreak(),
                *self.treatment(),
                PageBreak(),
                *self.architecture(),
                PageBreak(),
                *self.review(),
                *self.comparison(),
            ],
            canvasmaker=_NumberedCanvas,
        )
        return result.getvalue()


def build_styled_risk_pdf(
    payload: PremiumReportPayload, document: ThreatModelDocument, *, analysis_generated: bool = False
) -> bytes:
    return _Report(payload, document, analysis_generated=analysis_generated).build()
