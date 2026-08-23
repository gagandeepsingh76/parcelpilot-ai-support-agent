import os
import sys
import importlib

# Expose the backend/app package as the top-level `app` package.
# By setting __path__ we turn this shim into a namespace package that forwards
# submodule imports to the actual implementation located in backend/app.
_current_dir = os.path.abspath(os.path.dirname(__file__))
_backend_app_path = os.path.abspath(os.path.join(_current_dir, "..", "backend", "app"))
if not os.path.isdir(_backend_app_path):
    raise ImportError("Unable to locate backend/app directory for shim package 'app'.")
# Declare this package's __path__ so that imports like `from app.access import ...`
# resolve to modules inside backend/app.
__path__ = [_backend_app_path]

# Export __version__ from the actual backend.app package for compatibility.
_backend_pkg = importlib.import_module('backend.app')
__version__ = getattr(_backend_pkg, '__version__', '0.0.0')

