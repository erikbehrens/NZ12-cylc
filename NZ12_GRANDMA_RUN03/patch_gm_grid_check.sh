#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import shutil
import sys

p = Path(sys.argv[1])
s = p.read_text()

marker = '      ! GM HARDCODE NAMCTL - temporary diagnostic'

if 'GM GRID CHECK:' in s:
    sys.exit("Grid diagnostic already installed")

if s.count(marker) != 1:
    sys.exit("Expected exactly one hardcode marker")

diagnostic = """      WRITE(*,*) 'GM GRID CHECK:', narea, &
         ' Agrif_Root=', Agrif_Root(), &
         ' fixedrank=', Agrif_Curgrid%fixedrank
      FLUSH(6)
"""

shutil.copy2(p, str(p) + '.bak_before_gm_grid_check')
s = s.replace(marker, diagnostic + marker, 1)

p.write_text(s)
print("Patched:", p)
PY
