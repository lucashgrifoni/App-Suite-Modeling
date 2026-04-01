"""Aplicacao de teste: Saude (agendamento e prontuario leve)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class User:
    user_id: str
    role: str  # patient | professional | admin
    name: str


@dataclass
class Appointment:
    appointment_id: str
    patient_id: str
    professional_id: str
    when_iso: str
    status: str


@dataclass
class HealthApp:
    users: dict[str, User] = field(default_factory=dict)
    records: dict[str, list[str]] = field(default_factory=dict)
    documents: dict[str, list[Path]] = field(default_factory=dict)
    appointments: list[Appointment] = field(default_factory=list)
    notifications: list[str] = field(default_factory=list)
    audit_log: list[str] = field(default_factory=list)

    def register(self, user_id: str, role: str, name: str) -> User:
        user = User(user_id=user_id, role=role, name=name)
        self.users[user_id] = user
        self.records.setdefault(user_id, [])
        self.documents.setdefault(user_id, [])
        self.audit_log.append(f"register:{user_id}:{role}")
        return user

    def login(self, user_id: str) -> User:
        if user_id not in self.users:
            raise ValueError("usuario nao encontrado")
        self.audit_log.append(f"login:{user_id}")
        return self.users[user_id]

    def add_record_note(self, actor: User, patient_id: str, note: str) -> None:
        if actor.role not in {"professional", "admin"}:
            self.audit_log.append(f"record_update_blocked_role:{actor.user_id}:{patient_id}")
            raise PermissionError("somente profissional/admin altera prontuario")
        self.records[patient_id].append(note)
        self.audit_log.append(f"record_update:{actor.user_id}:{patient_id}")

    def view_record(self, actor: User, patient_id: str) -> list[str]:
        if actor.role == "patient" and actor.user_id != patient_id:
            self.audit_log.append(f"record_read_blocked_patient:{actor.user_id}:{patient_id}")
            raise PermissionError("paciente nao pode ver prontuario de terceiros")
        if actor.role == "professional" and not any(
            a.patient_id == patient_id and a.professional_id == actor.user_id for a in self.appointments
        ):
            # regra simplificada: profissional deve ter consulta com o paciente
            self.audit_log.append(f"record_read_blocked_professional:{actor.user_id}:{patient_id}")
            raise PermissionError("profissional sem vinculo clinico")
        self.audit_log.append(f"record_read:{actor.user_id}:{patient_id}")
        return self.records[patient_id]

    def schedule(self, actor: User, patient_id: str, professional_id: str, when_iso: str) -> Appointment:
        if actor.role not in {"patient", "admin"}:
            self.audit_log.append(f"schedule_blocked_role:{actor.user_id}:{patient_id}")
            raise PermissionError("somente paciente/admin agenda")
        if actor.role == "patient" and actor.user_id != patient_id:
            self.audit_log.append(f"schedule_blocked_patient:{actor.user_id}:{patient_id}")
            raise PermissionError("paciente nao pode agendar para outro")
        appointment = Appointment(
            appointment_id=f"apt-{len(self.appointments)+1}",
            patient_id=patient_id,
            professional_id=professional_id,
            when_iso=when_iso,
            status="scheduled",
        )
        self.appointments.append(appointment)
        self.notifications.append(f"mock_notify:consulta_agendada:{appointment.appointment_id}")
        self.audit_log.append(f"schedule:{actor.user_id}:{appointment.appointment_id}")
        return appointment

    def cancel(self, actor: User, appointment_id: str) -> None:
        apt = next(a for a in self.appointments if a.appointment_id == appointment_id)
        if actor.role == "patient" and actor.user_id != apt.patient_id:
            self.audit_log.append(f"cancel_blocked_patient:{actor.user_id}:{appointment_id}")
            raise PermissionError("paciente nao pode cancelar consulta de terceiro")
        if actor.role == "professional" and actor.user_id != apt.professional_id:
            self.audit_log.append(f"cancel_blocked_professional:{actor.user_id}:{appointment_id}")
            raise PermissionError("profissional nao pode cancelar consulta de terceiro")
        apt.status = "cancelled"
        self.notifications.append(f"mock_notify:consulta_cancelada:{appointment_id}")
        self.audit_log.append(f"cancel:{actor.user_id}:{appointment_id}")

    def upload_document(self, actor: User, patient_id: str, content: str, label: str) -> Path:
        if actor.role == "patient" and actor.user_id != patient_id:
            self.audit_log.append(f"document_upload_blocked_patient:{actor.user_id}:{patient_id}")
            raise PermissionError("upload nao autorizado")
        if actor.role == "professional":
            self.audit_log.append(f"document_upload_blocked_professional:{actor.user_id}:{patient_id}")
            raise PermissionError("profissional nao faz upload direto nesse fluxo")
        base = Path("artifacts/test-app-validation/health/documents")
        base.mkdir(parents=True, exist_ok=True)
        p = base / f"{patient_id}-{label}.txt"
        p.write_text(content, encoding="utf-8")
        self.documents[patient_id].append(p)
        self.audit_log.append(f"document_upload:{actor.user_id}:{patient_id}:{p.name}")
        return p

    def list_documents(self, actor: User, patient_id: str) -> list[str]:
        if actor.role == "patient" and actor.user_id != patient_id:
            self.audit_log.append(f"document_list_blocked_patient:{actor.user_id}:{patient_id}")
            raise PermissionError("listar documentos nao autorizado")
        if actor.role == "professional" and not any(
            a.patient_id == patient_id and a.professional_id == actor.user_id for a in self.appointments
        ):
            self.audit_log.append(f"document_list_blocked_professional:{actor.user_id}:{patient_id}")
            raise PermissionError("profissional sem relacao de atendimento")
        self.audit_log.append(f"document_list:{actor.user_id}:{patient_id}")
        return [p.name for p in self.documents[patient_id]]


def run_smoke() -> None:
    app = HealthApp()
    admin = app.register("adm-1", "admin", "Admin")
    patient = app.register("pat-1", "patient", "Paciente")
    patient2 = app.register("pat-2", "patient", "Paciente2")
    doctor = app.register("pro-1", "professional", "Dra")
    app.login(patient.user_id)
    apt = app.schedule(patient, patient.user_id, doctor.user_id, datetime.now(timezone.utc).isoformat())
    app.add_record_note(doctor, patient.user_id, "Paciente sem sinais de alarme")
    app.upload_document(patient, patient.user_id, "exame simples", "exame")
    try:
        app.view_record(patient2, patient.user_id)
        raise AssertionError("deveria bloquear acesso indevido a prontuario")
    except PermissionError:
        pass
    try:
        app.list_documents(patient2, patient.user_id)
        raise AssertionError("deveria bloquear leitura indevida de documentos")
    except PermissionError:
        pass
    assert app.view_record(admin, patient.user_id)
    assert app.list_documents(doctor, patient.user_id)
    app.cancel(patient, apt.appointment_id)
    assert all("pat-1" not in n and "pro-1" not in n for n in app.notifications)
    assert any("record_read_blocked_patient" in item for item in app.audit_log)
    print("health_smoke_ok")


if __name__ == "__main__":
    run_smoke()
