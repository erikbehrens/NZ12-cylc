#!/bin/bash

PATH=${FCM_MAKE_NEMO_RUN}/extract/nemo/ext/FCM/bin:$PATH

pproccfg=${CYLC_WORKFLOW_RUN_DIR}/app/fcm_preproc_agrif/file/bld_preproagr.cfg

[   -d ${FCM_MAKE_NEMO_RUN}/WORK ] || \mkdir -p ${FCM_MAKE_NEMO_RUN}/WORK
[   -d ${PPRNEMO}/ppsrc/nemo     ] || \mkdir -p ${PPRNEMO}/ppsrc/nemo
[   -d ${PPRNEMO}/inc            ] || \mkdir -p ${PPRNEMO}/inc
[   -d ${PPRNEMO}/obj            ] || \mkdir -p ${PPRNEMO}/obj

if [ "${AGRIF}" = True ] ; then
   
   for comp in ${SRCNEMO[*]}; do
       find $comp -name \*.[Ffh]90 -exec ln -sf {} ${FCM_MAKE_NEMO_RUN}/WORK \;
   done

   cat > ${pproccfg} << EOF

# ----------------------- FCM extract configuration file -----------------------
cfg::type                           bld
cfg::version                        1.0


# ------------------------------------------------------------------------------
# Build information
# ------------------------------------------------------------------------------

search_src           1

src::nemo    ${FCM_MAKE_NEMO_RUN}/WORK

bld::target  nemo.f90 agrif_user.f90 agrif2model.f90

dir::root    ${PPRNEMO}

bld::tool::fc_output
bld::tool::fc_compile
bld::tool::fc_include
bld::tool::fc        ${AGRIFEXE} ${FCM_MAKE_NEMO_RUN}
bld::tool::fflags
bld::tool::ld
bld::tool::ldflags
bld::tool::ar
bld::tool::arflags
bld::tool::make      gmake

OUTFILE_EXT::obj   .f90

# Pre-process code before analysing dependencies
bld::pp::nemo     1
bld::pp::nemo/agrif2model     0
bld::tool::cpp       cpp
bld::tool::fpp       cpp
bld::tool::fppflags::nemo  -P -E -traditional-cpp

inc ${FCM_MAKE_NEMO_APP}/file/cpp.cfg

# Ignore the following dependencies
bld::excl_dep        inc::netcdf.inc
bld::excl_dep        inc::VT.inc
bld::excl_dep        use::netcdf
bld::excl_dep        h::netcdf.inc
bld::excl_dep        h::mpif.h
bld::excl_dep        inc::mpif.h
bld::excl_dep        inc::mpe_logf.h
bld::excl_dep        use::mpi
bld::excl_dep        use::mod_oasis
bld::excl_dep        use::mkl_dfti
bld::excl_dep        use::nc4interface
bld::excl_dep        use::ioipsl
bld::excl_dep        use::ppr_1d
bld::excl_dep        use::xios
bld::excl_dep        use::agrif_grids
bld::excl_dep        use::agrif_types
bld::excl_dep        use::agrif_util
bld::excl_dep        inc::SetNumberofcells.h
bld::excl_dep        inc::GetNumberofcells.h
bld::excl_dep        inc::include_use_Alloc_agrif.h
bld::excl_dep        inc::allocations_calls_agrif.h
bld::excl_dep        inc::modtype_agrif.h
bld::excl_dep        inc::probdim_agrif.h
bld::excl_dep        inc::keys_agrif.h
bld::excl_dep        h::SetNumberofcells.h
bld::excl_dep        h::GetNumberofcells.h
bld::excl_dep        h::include_use_Alloc_agrif.h
bld::excl_dep        h::allocations_calls_agrif.h
bld::excl_dep        h::modtype_agrif.h
bld::excl_dep        h::probdim_agrif.h
bld::excl_dep        h::keys_agrif.h
bld::excl_dep        use::mod_attribut
bld::excl_dep        use::mod_event_client
bld::excl_dep        use::mod_ioclient
#bld::excl_dep        OBJ

# Don't generate interface files
bld::tool::geninterface none

# Allow ".h90" and ".f90" as an extension for CPP include files
bld::infile_ext::h90  CPP::INCLUDE
bld::infile_ext::f90  FPP::FPP9X::SOURCE
bld::src_type::nemo/agrif2model.F90 FORTRAN::FORTRAN9X::SOURCE
EOF

   echo `which fcm`
   fcm build --ignore-lock -j 1 ${pproccfg}

else

   SRC_OCE=${SRCNEMO}/OCE
   SRC_ICE=${SRCNEMO}/ICE
   for comp in ${SRC_OCE[*]}; do
       find $comp -name \*.[Ffh]90 -exec ln -sf {} ${PPRNEMO}/obj \;
   done
   for comp in ${SRC_ICE[*]}; do
       find $comp -name \*.[Ffh]90 -exec ln -sf {} ${PPRNEMO}/obj \;
   done

fi
