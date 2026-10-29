"""Legacy shim: Vercel uses admin_web.app:app via pyproject.toml entrypoint."""
from admin_web.app import app

__all__ = ["app"]
