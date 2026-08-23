import os, importlib
_current_dir = os.path.abspath(os.path.dirname(__file__))
_backend_insights_path = os.path.abspath(os.path.join(_current_dir, "..", "backend", "app", "insights"))
if not os.path.isdir(_backend_insights_path):
    raise ImportError("Unable to locate backend/app/insights for shim package 'app.insights'.")
__path__ = [_backend_insights_path]
# Export version if needed
_backend_pkg = importlib.import_module('backend.app')
__version__ = getattr(_backend_pkg, '__version__', '0.0.0')

