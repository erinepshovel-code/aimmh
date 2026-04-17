from pathlib import Path

_PART_FILES = ['test_iteration10_features.py.part01.txt', 'test_iteration10_features.py.part02.txt']
_PART_DIR = Path(__file__).resolve().parent
_EXEC_SOURCE = "".join((_PART_DIR / _part).read_text(encoding="utf-8") for _part in _PART_FILES)
exec(compile(_EXEC_SOURCE, __file__, "exec"))
