#!/bin/bash

PATH=${FCM_MAKE_NEMO_RUN}/extract/nemo/ext/FCM/bin:$PATH

convcfg=${CYLC_WORKFLOW_RUN_DIR}/app/fcm_build_conv/file/conv.cfg
agrifsrc=${FCM_MAKE_NEMO_RUN}/extract/nemo/ext/AGRIF/LIB
agriflib=${FCM_MAKE_NEMO_RUN}/AGRIFLIB

if [ "${AGRIF}" = True ] ; then

   cat > ${convcfg} << EOF

# ----------------------- FCM extract configuration file -----------------------
# template to compile agrif conv, currently not used
cfg::type                           bld
cfg::version                        1.0

# ------------------------------------------------------------------------------
# Build information
# ------------------------------------------------------------------------------
bld::tool::cc        cc -Wl,"--allow-multiple-definition"
#bld::tool::cflags    -O3 -g
bld::tool::cflags    -O3 -g
bld::tool::make      gmake

src::convsrc  ${agrifsrc}

 #----------------------------------------------------------------------------
# Build options (code-specific, machine-independent)
# ----------------------------------------------------------------------------
dir::root            ${agriflib}

bld::exe_name::main conv
bld::target                              libconvsrc.a  fortran.o main.o  conv
bld::exe_dep::conv
EOF

   echo `which cc`
   echo `cc --version`
   echo `which fcm`
   fcm build ${convcfg}

fi
