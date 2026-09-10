"""Limitador acotado de intentos fallidos de autenticación por cuenta."""

from collections import OrderedDict, deque
from hashlib import sha256
from threading import Lock
from time import monotonic

from app.core.errors import AppError

MAX_TRACKED_KEYS = 10_000


def login_key(correo: str) -> str:
    """Evita conservar correos en claro dentro del estado temporal del proceso."""
    return sha256(correo.strip().lower().encode("utf-8")).hexdigest()


class LoginThrottle:
    def __init__(self) -> None:
        self._attempts: OrderedDict[str, deque[float]] = OrderedDict()
        self._lock = Lock()

    @staticmethod
    def _prune(attempts: deque[float], now: float, window_seconds: int) -> None:
        cutoff = now - window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

    def ensure_allowed(
        self, key: str, *, max_attempts: int, window_seconds: int, now: float | None = None,
    ) -> None:
        current = monotonic() if now is None else now
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                return
            self._prune(attempts, current, window_seconds)
            if not attempts:
                del self._attempts[key]
                return
            self._attempts.move_to_end(key)
            if len(attempts) >= max_attempts:
                raise AppError(
                    "TOO_MANY_LOGIN_ATTEMPTS",
                    "Demasiados intentos fallidos. Intente nuevamente en unos minutos.",
                    429,
                )

    def register_failure(
        self, key: str, *, window_seconds: int, now: float | None = None,
    ) -> None:
        current = monotonic() if now is None else now
        with self._lock:
            attempts = self._attempts.get(key)
            if attempts is None:
                if len(self._attempts) >= MAX_TRACKED_KEYS:
                    self._attempts.popitem(last=False)
                attempts = deque()
                self._attempts[key] = attempts
            self._prune(attempts, current, window_seconds)
            attempts.append(current)
            self._attempts.move_to_end(key)

    def clear(self, key: str | None = None) -> None:
        with self._lock:
            if key is None:
                self._attempts.clear()
            else:
                self._attempts.pop(key, None)
