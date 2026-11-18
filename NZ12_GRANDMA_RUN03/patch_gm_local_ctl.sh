#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import shutil
import sys

p = Path(sys.argv[1])
s = p.read_text()

if 'GM LOCAL CTL TEST' in s:
    sys.exit("Patch already applied")

target = 'READ_NML_REF(numnam,namctl)'
if s.count(target) != 1:
    sys.exit(f"Expected one reference read, found {s.count(target)}")

# Insert a contained procedure at module scope, before the first
# module procedure. This avoids putting a new CONTAINS inside nemo_init.
anchor = '   SUBROUTINE nemo_init'
if anchor not in s:
    sys.exit("Could not find nemo_init")

backup = Path(str(p) + '.bak_gm_local_ctl')
shutil.copy2(p, backup)

routine = """
   ! GM LOCAL CTL TEST
   SUBROUTINE gm_test_namctl(buffer, irank)
      USE in_out_manager, ONLY : sn_ctl
      CHARACTER(LEN=*), INTENT(IN) :: buffer
      INTEGER, INTENT(IN) :: irank

      TYPE(sn_ctl) :: sn_cfctl
      LOGICAL :: ln_timing, ln_diacfl
      INTEGER :: nn_isplt, nn_jsplt
      INTEGER :: nn_ictls, nn_ictle, nn_jctls, nn_jctle
      INTEGER :: ios, ipos

      NAMELIST /namctl/ sn_cfctl, ln_timing, ln_diacfl, &
         nn_isplt, nn_jsplt, nn_ictls, nn_ictle, &
         nn_jctls, nn_jctle

      ipos = MAX(INDEX(buffer,'&namctl '),1)

      WRITE(*,*) 'GM CTL TEST A:', irank
      FLUSH(6)

      READ(buffer(ipos:),NML=namctl,IOSTAT=ios)

      WRITE(*,*) 'GM CTL TEST B:', irank, ios
      FLUSH(6)
   END SUBROUTINE gm_test_namctl

"""

s = s.replace(anchor, routine + anchor, 1)

# Run the diagnostic immediately before the original read.
s = s.replace(
    target,
    "CALL gm_test_namctl(numnam_ref,narea)\n      " + target,
    1
)

p.write_text(s)
print("Patched:", p)
print("Backup:", backup)
PY
