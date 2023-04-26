from typing import Any, Dict, Optional, TypeVar

_T = TypeVar("_T")
_RT = TypeVar("_RT")


def dictchangekey(d: Dict[_T, _RT], oldkey: _T, newkey: _T) -> Optional[_RT]:
    if oldkey not in d:
        return None
    if newkey in d:
        raise ValueError("新的key已经在字典中")

    d[newkey] = d.pop(oldkey)
    return d[newkey]


def manydictchangekey(oldkey: _T, newkey: _T, *args: Dict[_T, Any]):
    for d in args:
        dictchangekey(d, oldkey, newkey)


def dictpop(d: Dict[_T, _RT], key: _T) -> _RT:
    return d.pop(key) if key in d else None
