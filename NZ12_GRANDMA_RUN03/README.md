# NZ12_GRANDMA_RUN03 — Modification Record

*NEMO5 / AGRIF online coarsening · Status: 3 November 2026*

## Purpose and grid layout

Two grids only:

| AGRIF level | Grid | Dimensions | Role |
|---|---|---|---|
| −1 | Grandmother, 0.75° | 480 × 403 × 75 | TOP/PISCES |
| 0 | Root, 0.25° | 1440 × 1206 × 75 | Ocean physics |

No conventional +1 child. Refinement ratio **3 × 3**; fixed vertical layers, linear free surface, and RK3.

## Locations

- **NEMO source:** `/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo`
- **Persistent Cylc source:** `/home/behrense/NZ12-cylc/NZ12_GRANDMA_RUN03`
- **Installed workflow:** `/home/behrense/cylc-run/NZ12_GRANDMA_RUN03/run1`
- **Ancillaries:** `/home/behrense/_niwa02764/erik/GOSI10p3_ancils/GOSI10p3_eORCA025_coarse_TOP_ancils`

## NEMO / AGRIF source changes

Paths below are relative to the NEMO source directory.

| File | Change |
|---|---|
| `src/OCE/nemogcm.F90` | Grandmother initialization; load `gm_namelist_ref` and `gm_namelist_cfg` for grandmother and standard namelists for root; restore `namctl` reading. |
| `src/OCE/DOM/domain.F90` | Do not scale `rn_Dt` by `Agrif_Rhot()` for grandmother; scale only for conventional children. |
| `src/OCE/LBC/lib_mpp.F90` | Diagnostic prints in `load_nml` for grandmother namelists: rank and `ldwp`, around line 1555. Verified in source; not yet verified in rebuilt executable. |
| `ext/AGRIF/AGRIF_FILES/modutil.F90` | Grandmother grid construction and initialization modifications. |
| `ext/AGRIF/AGRIF_FILES/modcluster.F90` | AGRIF hierarchy and grid-pointer modifications. |

Grandmother namelist selection in `nemogcm.F90`:

```fortran
IF (Agrif_Curgrid%grand_mother_grid) THEN
   CALL load_nml( numnam_ref, 'gm_namelist_ref', -1, lwm )
   CALL load_nml( numnam_cfg, 'gm_namelist_cfg', -1, lwm )
ELSE
   CALL load_nml( numnam_ref, 'namelist_ref', -1, lwm )
   CALL load_nml( numnam_cfg, 'namelist_cfg', -1, lwm )
ENDIF
```

Timestep guard in `domain.F90`:

```fortran
IF( .NOT. Agrif_Root() .AND. .NOT. Agrif_Curgrid%grand_mother_grid ) THEN
   rn_Dt = Agrif_Parent(rn_Dt) / Agrif_Rhot()
ENDIF
```

## Cylc workflow changes

Paths below are relative to the persistent Cylc source directory.

| File | Change |
|---|---|
| `rose-suite.conf` | `AGRIF=true`; `NUM_ZOOMS=0`; `OCEAN_ICE_OPT_KEYS` empty. |
| `app/nemo/file/AGRIF_FixedGrids.in` | Grandmother with 3 × 3 ratio, zero children. |
| `app/nemo/rose-app.conf` | Fine `domain_cfg.nc` from ancillary `1_domain_cfg.nc`; coarse `gm_domain_cfg.nc` from ancillary `domain_cfg.nc`; stage grandmother namelists; root `ln_agrif_GrandMa=false`. |
| `app/nemo/file/gm_namelist_cfg` | Grandmother `ln_agrif_GrandMa=true`; contains `namctl`. |
| `app/nemo/opt/rose-app-agrif.conf` | `iodef.xml` source points to local `iodef_0_server.xml`. |
| `app/nemo/file/iodef_0_server.xml` | Derived from `iodef_1_server.xml`, removing the `1_nemo` child context while retaining XIOS3 `p2p` and `services_use_window_manager=false`. |
| `local_drivers/Coupled_Drivers/nemo_driver.py` | Change `.split(' ')` to `.split()` to tolerate `AGRIF_DOMAINS=""`; persistent `flow.cylc` build override needs verification. |

`app/nemo/file/AGRIF_FixedGrids.in`:

```text
-1 3 3 1 1
0
```

XIOS staging in `app/nemo/opt/rose-app-agrif.conf`:

```ini
[file:iodef.xml]
source=${ROSE_SUITE_DIR}/app/nemo/file/iodef_0_server.xml
```

## Current runtime status

The earlier XIOS error (`Can not open ./1_context_nemo.xml`) was addressed by removing the conventional child context and reinstalling Cylc. The model now reaches AGRIF grandmother initialization but aborts with **`MPI_Abort(123)`**.

Last trace:

```text
AGRIF GM BEFORE 5
GM INIT A: before get_grid_comm
GM INIT B: communicator -2080374782
LOAD_NML:gm_namelist_ref allocated= F rank= ...
```

Both grandmother namelist files are staged: `gm_namelist_ref` (124,159 bytes) and `gm_namelist_cfg` (11,515 bytes).

**Unresolved grid discrepancy:** AGRIF internal grandmother dimensions are **480 × 402**, whereas coarse `domain_cfg.nc` is **480 × 403**. The immediate investigation is the `load_nml` I/O rank (`ldwp`) and MPI communicator/broadcast behavior; neither is confirmed as the cause yet.

## Next steps

1. Rebuild NEMO with the `lib_mpp.F90` diagnostic and inspect `GM LOAD_NML` rank/`ldwp` output.
2. Trace the grandmother namelist-loading failure, including MPI communicator and broadcast.
3. Resolve the 480 × 402 versus 480 × 403 dimensions; validate grandmother initialization and XIOS context.
4. Verify fine-physics-to-coarse-TOP/PISCES coupling, tracer activation, and multi-step integration.

**Deployment:** Run `cylc reinstall` after persistent workflow-source changes; rebuild and deploy the NEMO executable after Fortran changes.
# NZ12_GRANDMA_RUN03
