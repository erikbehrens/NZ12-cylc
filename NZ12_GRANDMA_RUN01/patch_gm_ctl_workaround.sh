#!/bin/bash
set -euo pipefail

FILE=/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo/src/OCE/nemogcm.F90

python3 - "$FILE" <<'PY'
from pathlib import Path
import re, shutil, sys

p = Path(sys.argv[1])
s = p.read_text()

if 'GM CTL WORKAROUND' in s:
    sys.exit("Already patched")

if s.count('READ_NML_REF(numnam,namctl)') != 1:
    sys.exit("Expected one reference namctl read")

if s.count('READ_NML_CFG(numnam,namctl)') != 1:
    sys.exit("Expected one configuration namctl read")

pattern = (
    r'(?ms)^[ \t]*!\s*GM LOCAL CTL TEST.*?'
    r'^[ \t]*END SUBROUTINE gm_test_namctl[^\n]*'
)
if len(re.findall(pattern, s)) != 1:
    sys.exit("Diagnostic subroutine not found")

routine = """
   ! GM CTL WORKAROUND
   SUBROUTINE gm_read_namctl(buffer, ctl_out, timing_out, diacfl_out, &
                             isplt_out, jsplt_out, ictls_out, ictle_out, &
                             jctls_out, jctle_out, ios)
      USE in_out_manager, ONLY : sn_ctl
      CHARACTER(LEN=*), INTENT(IN) :: buffer
      TYPE(sn_ctl), INTENT(INOUT) :: ctl_out
      LOGICAL, INTENT(INOUT) :: timing_out, diacfl_out
      INTEGER, INTENT(INOUT) :: isplt_out, jsplt_out
      INTEGER, INTENT(INOUT) :: ictls_out, ictle_out
      INTEGER, INTENT(INOUT) :: jctls_out, jctle_out
      INTEGER, INTENT(OUT) :: ios

      TYPE(sn_ctl) :: sn_cfctl
      LOGICAL :: ln_timing, ln_diacfl
      INTEGER :: nn_isplt, nn_jsplt
      INTEGER :: nn_ictls, nn_ictle, nn_jctls, nn_jctle
      INTEGER :: ipos

      NAMELIST /namctl/ sn_cfctl, ln_timing, ln_diacfl, &
         nn_isplt, nn_jsplt, nn_ictls, nn_ictle, &
         nn_jctls, nn_jctle

      sn_cfctl  = ctl_out
      ln_timing = timing_out
      ln_diacfl = diacfl_out
      nn_isplt  = isplt_out
      nn_jsplt  = jsplt_out
      nn_ictls  = ictls_out
      nn_ictle  = ictle_out
      nn_jctls  = jctls_out
      nn_jctle  = jctle_out

      ipos = MAX(INDEX(buffer,'&namctl '),1)
      READ(buffer(ipos:),NML=namctl,IOSTAT=ios)

      IF (ios == 0) THEN
         ctl_out    = sn_cfctl
         timing_out = ln_timing
         diacfl_out = ln_diacfl
         isplt_out  = nn_isplt
         jsplt_out  = nn_jsplt
         ictls_out  = nn_ictls
         ictle_out  = nn_ictle
         jctls_out  = nn_jctls
         jctle_out  = nn_jctle
      ENDIF
   END SUBROUTINE gm_read_namctl
"""

shutil.copy2(p, str(p) + '.bak_before_gm_ctl_workaround')

s = re.sub(pattern, routine, s, count=1)

# Remove diagnostic call.
s, n = re.subn(
    r'(?m)^[ \t]*CALL gm_test_namctl\(numnam_ref,narea\)[ \t]*\n',
    '',
    s
)
if n != 1:
    sys.exit("Expected one diagnostic call")

args = (
    'sn_cfctl, ln_timing, ln_diacfl, &\n'
    '         nn_isplt, nn_jsplt, nn_ictls, nn_ictle, &\n'
    '         nn_jctls, nn_jctle, ios'
)

s = s.replace(
    'READ_NML_REF(numnam,namctl)',
    'CALL gm_read_namctl(numnam_ref, ' + args + ')\n'
    "      CALL ctl_nam(ios,'namctl (ref)',.TRUE.)",
    1
)

s = s.replace(
    'READ_NML_CFG(numnam,namctl)',
    'CALL gm_read_namctl(numnam_cfg, ' + args + ')\n'
    "      CALL ctl_nam(ios,'namctl (cfg)',.FALSE.)",
    1
)

p.write_text(s)
print("Patched:", p)
PY
