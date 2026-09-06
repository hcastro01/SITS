"""Router de Dashboard. Espejo de Code.gs::getDashboardData -> TSSearch.dashboard()."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.core.permissions import AuthenticatedUser
from app.services.dashboard import get_dashboard

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])


@router.get("")
def obtener(db: Session = Depends(get_db), user: AuthenticatedUser = Depends(get_current_user)):
    return get_dashboard(db, user)
