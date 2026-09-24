"""Inspect the effective tasks and their input contracts without calling a model."""
from . import get_prompt_manager, BUNDLE_VERSION

def list_tasks():
    manager = get_prompt_manager()
    return [{"task_id":name,"bundle_version":BUNDLE_VERSION,"variables":sorted(manager.variables(name))}
            for name in manager.list_templates() if not name.startswith("shared/")]
