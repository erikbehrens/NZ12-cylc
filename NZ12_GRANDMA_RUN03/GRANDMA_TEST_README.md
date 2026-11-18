# Grandmother MY_TRC test (adapted from RUN03 XIOS 1051)

NEMO checkout: `/home/behrense/_niwa02764/erik/AGRIF_COARSE/nemo`.

Changes: local source extraction; `src/TOP` included; `key_top` added (the existing preprocessor task appends `key_agrif`); root `ln_agrif_GrandMa=.true.`, `ln_top=.true.`; child `ln_top=.false.`; one MY_TRC unit tracer (`jp_bgc=1`) and FCT advection. FixedGrids 3:1 and coarse/fine domain cfg paths updated.

**Before running:**
1. Confirm `/home/behrense/_niwa02764/erik/GOSI10p3_ancils/GOSI10p3_eORCA025_coarse_TOP_ancils` has `domain_cfg.nc` (480x403) and `1_domain_cfg.nc` (1440x1206); these paths are assumptions.
2. The original suite retains many GOSI10p0 paths, forcing, restart, XIOS XML, and 1051-rank layout. They have **not** been validated against NEMO 5 / the new grandmother grid. Update those to matching ancillaries and XIOS definitions.
3. `namelist_top_cfg` and `namelist_top_ref` are bundled; check NEMO 5 namelist compatibility. Confirm TOP reads `ln_rsttr=.false.` for the cold tracer start (while ocean can restart).
4. `fcm_git_path` is a no-op; `fcm_make_ocean` extracts the local checkout. Verify FCM accepts local primary source and that required `ext/` paths exist.
5. The existing Rose application is NEMO 4.2-era and may need further porting to NEMO 5; **not tested** on HPC.
6. Check TOP outputs (MY_TRC field) are declared in XIOS and add a global tracer inventory diagnostic.

