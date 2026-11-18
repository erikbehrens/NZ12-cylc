#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import re
import shutil
import sys

p = Path(sys.argv[1])
s = p.read_text()

if "GM BYPASS CTL:" in s:
    sys.exit("Already patched")

pattern = (
    r'(?s)([ \t]*!\s*GM HARDCODE NAMCTL - temporary diagnostic\n)'
    r'[ \t]*IF \(\.NOT\. Agrif_Root\(\)\) THEN\n'
    r'.*?'
    r'([ \t]*ELSE\n[ \t]*READ_NML_REF\(numnam,namctl\)\n'
    r'[ \t]*ENDIF)'
)

replacement = (
    r'\1'
    "      IF (.NOT. Agrif_Root()) THEN\n"
    "         WRITE(*,*) 'GM BYPASS CTL:', narea\n"
    "         FLUSH(6)\n"
    r'\2'
)

s2, n = re.subn(pattern, replacement, s, count=1)

if n != 1:
    sys.exit("Could not identify grandmother hardcode block")

shutil.copy2(p, str(p) + ".bak_before_gm_bypass")
p.write_text(s2)

print("Patched:", p)
PY
