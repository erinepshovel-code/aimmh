# "lines of code":"5","lines of commented":"0"
from pathlib import Path

_PART_FILES = ['chat.py.part01.txt', 'chat.py.part02.txt', 'chat.py.part03.txt']
_PART_DIR = Path(__file__).resolve().parent
_EXEC_SOURCE = "".join((_PART_DIR / _part).read_text(encoding="utf-8") for _part in _PART_FILES)
exec(compile(_EXEC_SOURCE, __file__, "exec"))
# "lines of code":"5","lines of commented":"0"
