#!/bin/bash
set -e
cd 6.1.0
docker build  --build-arg VER=6.1.0 -t greenplum-mne:6.1.0 .
docker tag greenplum-mne:6.1.0 smartivo.azurecr.io/greenplum-mne:6.1.0
