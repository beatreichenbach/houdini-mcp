import sys
import types
from collections.abc import Callable
from typing import TypeVar

Result = TypeVar('Result')


def _execute_in_main_thread(function: Callable[[], Result]) -> Result:
    return function()


hdefereval = types.ModuleType('hdefereval')
hdefereval.__dict__['executeInMainThreadWithResult'] = _execute_in_main_thread
sys.modules.setdefault('hdefereval', hdefereval)
