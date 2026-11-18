#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import shutil, sys

p = Path(sys.argv[1])
backup = Path(str(p) + '.bak_before_gm_ctl_workaround')

if not backup.exists():
    sys.exit(f"Missing backup: {backup}")

s = backup.read_text()

ref = 'READ_NML_REF(numnam,namctl)'
cfg = 'READ_NML_CFG(numnam,namctl)'

if s.count(ref) != 1 or s.count(cfg) != 1:
    sys.exit("Expected one reference and one configuration namctl read")

# Preserve the current source separately.
shutil.copy2(p, str(p) + '.bak_before_gm_hardcode')

hardcode = """
      ! GM HARDCODE NAMCTL - temporary diagnostic
      IF (.NOT. Agrif_Root()) THEN
         sn_cfctl%l_runstat = .FALSE.
         sn_cfctl%l_trcstat = .FALSE.
         sn_cfctl%l_oceout  = .FALSE.
         sn_cfctl%l_layout  = .FALSE.
         sn_cfctl%l_prtctl  = .FALSE.
         sn_cfctl%l_prttrc  = .FALSE.
         sn_cfctl%l_oasout  = .FALSE.
         sn_cfctl%l_obsstat = .FALSE.

         sn_cfctl%procmin  = 1
         sn_cfctl%procmax  = 999999
         sn_cfctl%procincr = 1
         sn_cfctl%ptimincr = 1

         ln_timing = .FALSE.
         ln_diacfl = .FALSE.

         WRITE(*,*) 'GM HARDCODE NAMCTL:', narea
         FLUSH(6)
      ELSE
         READ_NML_REF(numnam,namctl)
         READ_NML_CFG(numnam,namctl)
      ENDIF
"""

# Replace the original reference read with the conditional.
s = s.replace(ref, hardcode, 1)

# Remove the original configuration read, now inside the parent branch.
# Use the last occurrence because the parent read was inserted above.
pos = s.rfind(cfg)
if pos < 0:
    sys.exit("Configuration read not found")
s = s[:pos] + '! GM namctl configuration read handled above' + s[pos+len(cfg):]

# Remove the old diagnostic call, if present.
s = s.replace('CALL gm_test_namctl(numnam_ref,narea)', '')

p.write_text(s)
print("Patched:", p)
print("Saved previous source:", str(p) + '.bak_before_gm_hardcode')
PY
