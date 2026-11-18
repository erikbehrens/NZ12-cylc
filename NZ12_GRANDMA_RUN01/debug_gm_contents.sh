#!/bin/bash
set -euo pipefail

SRC="/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo"
FILE="$SRC/src/OCE/nemogcm.F90"

python3 - "$FILE" <<'PY'
from pathlib import Path
import sys

p = Path(sys.argv[1])
s = p.read_text()

if "GM CONTENT CHECK" in s:
    raise SystemExit("Already patched")

old = "      READ_NML_REF(numnam,namctl)"

new = """      IF (narea == 1 .AND. ALLOCATED(numnam_ref)) THEN
         WRITE(*,*) 'GM CONTENT CHECK root=', Agrif_Root(), &
            ' length=', LEN(numnam_ref)
         WRITE(*,*) 'GM CONTENT FIRST:', numnam_ref(1:80)
         WRITE(*,*) 'GM CONTENT LAST:', &
            numnam_ref(LEN(numnam_ref)-79:)
         WRITE(*,*) 'GM CONTENT SUM:', &
            SUM([(IACHAR(numnam_ref(ji:ji)), &
            ji=1,LEN(numnam_ref))])
         FLUSH(6)
      ENDIF
      READ_NML_REF(numnam,namctl)"""

# Use a block-local integer to avoid undeclared loop variable
new = new.replace(
    "      IF (narea == 1 .AND. ALLOCATED(numnam_ref)) THEN",
    "      BLOCK\n         INTEGER :: ji\n      IF (narea == 1 .AND. ALLOCATED(numnam_ref)) THEN"
).replace(
    "      READ_NML_REF(numnam,namctl)",
    "      END BLOCK\n      READ_NML_REF(numnam,namctl)"
)

if s.count(old) != 1:
    raise SystemExit(f"Expected one namctl read, found {s.count(old)}")

backup = Path(str(p) + ".bak_gm_contents")
backup.write_text(s)

p.write_text(s.replace(old, new, 1))
print("Patched:", p)
print("Backup:", backup)
PY
