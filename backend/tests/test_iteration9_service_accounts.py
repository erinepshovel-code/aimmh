from pathlib import Path

_PART_FILES = ['test_iteration9_service_accounts.py.part01.txt', 'test_iteration9_service_accounts.py.part02.txt', 'test_iteration9_service_accounts.py.part03.txt']
_PART_DIR = Path(__file__).resolve().parent
_EXEC_SOURCE = "".join((_PART_DIR / _part).read_text(encoding="utf-8") for _part in _PART_FILES)
exec(compile(_EXEC_SOURCE, __file__, "exec"))
