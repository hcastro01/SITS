"""Resumen operativo. Equivalente a Base Sistema/SearchService.gs::dashboard() (TSSearch.dashboard),
invocado desde Code.gs:27 (getDashboardData).

Base Sistema/Scripts.html:244 filtraba las tarjetas de KPI en el cliente según los permisos
del usuario (`.filter(item=>can(item[4],item[5]))`); aquí el filtro se hace en el servidor:
cada indicador solo se calcula y se incluye en la respuesta si el usuario tiene permiso de
lectura sobre el módulo correspondiente. El panel "Casos por estado" (barras) y "Prioridades"
(dona) del HTML legacy (Dashboard.html:19-27) nunca reciben datos reales en Scripts.html —
`dashboard()` no devuelve `casesByStatus`/`casosPorEstado` — así que no se portan: habría que
inventar esa agregación, y no existe evidencia de que haya funcionado nunca en producción.
"""

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.permissions import AuthenticatedUser, authorize, can
from app.models import Caso, Compromiso, Novedad, Recorrido, Seguimiento

_ABIERTOS_EXCLUIDOS = {"CERRADO", "INACTIVO"}
_PENDIENTES = {"BORRADOR", "PENDIENTE", "REGISTRADO"}
_COMPROMISO_CERRADOS = {"CUMPLIDO", "CERRADO", "CANCELADO"}
_NOVEDAD_CERRADAS = {"CERRADO", "RESUELTO"}


def _normalizar(valor: str | None) -> str:
    return (valor or "").strip().upper()


def get_dashboard(session: Session, user: AuthenticatedUser) -> dict:
    authorize(user, "DASHBOARD", "read")
    ahora = datetime.now(UTC).isoformat()
    hoy = ahora[:10]
    datos: dict = {"generatedAt": ahora}

    if can(user, "CASOS", "read"):
        casos = session.scalars(select(Caso).where(Caso.eliminado.is_(False))).all()
        datos["casesOpen"] = sum(1 for c in casos if _normalizar(c.estado_caso) not in _ABIERTOS_EXCLUIDOS)
        datos["casesClosed"] = sum(1 for c in casos if _normalizar(c.estado_caso) == "CERRADO")
        datos["casesPending"] = sum(1 for c in casos if _normalizar(c.estado_caso) in _PENDIENTES)

    if can(user, "SEGUIMIENTOS", "read"):
        seguimientos = session.scalars(select(Seguimiento).where(Seguimiento.eliminado.is_(False))).all()
        datos["upcomingFollowUps"] = sum(
            1 for s in seguimientos
            if s.fecha_proxima_accion and s.fecha_proxima_accion >= hoy and _normalizar(s.estado) != "CERRADO"
        )

    if can(user, "COMPROMISOS", "read"):
        compromisos = session.scalars(select(Compromiso).where(Compromiso.eliminado.is_(False))).all()
        datos["overdueCommitments"] = sum(
            1 for c in compromisos
            if c.fecha_limite and c.fecha_limite < hoy and _normalizar(c.estado) not in _COMPROMISO_CERRADOS
        )

    if can(user, "NOVEDADES", "read"):
        novedades = session.scalars(select(Novedad).where(Novedad.eliminado.is_(False))).all()
        datos["pendingNews"] = sum(1 for n in novedades if _normalizar(n.estado) not in _NOVEDAD_CERRADAS)

    if can(user, "RECORRIDOS", "read"):
        datos["toursCompleted"] = session.scalar(
            select(func.count()).select_from(Recorrido).where(Recorrido.eliminado.is_(False))
        )

    return datos
