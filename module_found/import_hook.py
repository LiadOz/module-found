import os
import sys
import importlib
from .lazy_object import LazyModule, ctx


DISALLOWED_MODULES = ["apport_python_hook", "sitecustomize", "usercustomize"]
class AiFinder():  # pylint: disable=too-few-public-methods
    def __init__(self, api_key: str) -> None:
        self._loader = AiLoader(api_key)

    def find_spec(self, fullname, path, _target=None):
        if path:
            return None
        if '.' in fullname or fullname in DISALLOWED_MODULES:
            return None
        return importlib.util.spec_from_loader(fullname, self._loader)


class AiLoader():
    def __init__(self, api_key: str) -> None:
        self._api_key = api_key

    def create_module(self, spec):
        return LazyModule(self._api_key, spec.name)

    def exec_module(self, _module):
        ...


def setup(api_key: str = '', model: str = ''):
    if sys.argv[0].endswith('pip'):
        # Some users have reported that they fail to use pip after the module-found is installed.
        # I don't understand why would someone use pip to install additional packages
        # if module-found actually contains all packages that exist and those that don't exist.
        # But to please them I added this return.
        return

    if not model:
        model = os.getenv('MODULE_FOUND_MODEL') or 'gpt-4o-mini'
    if not api_key:
        api_key = os.getenv('MODULE_FOUND_KEY')
    if api_key:
        ctx.set_api_params(api_key, model)
        sys.meta_path.append(AiFinder(api_key))
