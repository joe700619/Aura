import os
import importlib
import inspect
from .base import BaseRule

_rules_registry = {}

def get_all_rules():
    """
    獲取所有已註冊的規則實例清單。
    回傳 [RuleClass, RuleClass, ...]
    """
    if not _rules_registry:
        _load_all_rules()
    return list(_rules_registry.values())


def get_rule_by_code(code):
    """
    根據 rule_code 獲取對應的規則 Class
    """
    if not _rules_registry:
        _load_all_rules()
    return _rules_registry.get(code)


def _load_all_rules():
    """
    動態載入這個資料夾下所有的 python 模組，
    並將繼承自 BaseRule 的類別註冊到 registry 中。
    """
    current_dir = os.path.dirname(__file__)
    for filename in os.listdir(current_dir):
        if filename.endswith(".py") and not filename.startswith("__") and filename != "base.py":
            module_name = f".{filename[:-3]}"
            try:
                module = importlib.import_module(module_name, package=__package__)
                # 找出模組中所有繼承自 BaseRule 的類別 (排除 BaseRule 本身)
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if issubclass(obj, BaseRule) and obj is not BaseRule:
                        if hasattr(obj, 'code') and obj.code:
                            _rules_registry[obj.code] = obj
                        else:
                            print(f"Warning: Rule class {obj.__name__} missing 'code' attribute.")
            except ImportError as e:
                print(f"Error loading rule module {module_name}: {e}")

