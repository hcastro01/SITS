"""Adaptador WSGI para PythonAnywhere. La aplicación nativa continúa siendo ASGI."""

from a2wsgi import ASGIMiddleware

from app.main import app

application = ASGIMiddleware(app)
