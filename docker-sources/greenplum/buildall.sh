#!/bin/bash
set -e
cd 6.2.1
docker build  --build-arg VER=6.2.1 -t greenplum-mne:6.2.1 .
cd ..
#docker tag greenplum-mne:6.2.1 smartivo.azurecr.io/greenplum-mne:6.2.1
