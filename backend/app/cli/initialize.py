"""Aplica migraciones y catálogos base sin iniciar el servidor web."""

from app.start import initialize


if __name__ == "__main__":
    initialize()
    print("Base de datos actualizada y catálogos verificados.")
