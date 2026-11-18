#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import shutil
import sys

p = Path(sys.argv[1])
s = p.read_text()

if 'GM CTL VALUES:' in s:
    sys.exit("Diagnostic already installed")

marker = '      IF( narea < sn_cfctl%procmin'

if s.count(marker) != 1:
    sys.exit(f"Expected one finalization check, found {s.count(marker)}")

diagnostic = """      ! GM CTL VALUES diagnostic
      IF (.NOT. Agrif_Root()) THEN
         WRITE(*,*) 'GM CTL VALUES:', narea, &
            sn_cfctl%procmin, sn_cfctl%procmax, &
            sn_cfctl%procincr, sn_cfctl%ptimincr
         FLUSH(6)
      ENDIF
"""

shutil.copy2(p, str(p) + '.bak_before_gm_ctl_values')
s = s.replace(marker, diagnostic + marker, 1)

p.write_text(s)
print("Patched:", p)
PY
