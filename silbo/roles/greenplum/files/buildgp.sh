#!/bin/bash
set -e
cd 6.1.0
wget -O "greenplum-db-6.1.0-rhel7-x86_64.rpm" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/495851/product_files/521998/download
wget -O "plr-3.0.3-gp6-rhel7-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/495851/product_files/522002/download
wget -O "postgis-2.1.5+pivotal.2-4-gp6-rhel7-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/495851/product_files/522048/download
wget -O "greenplum-cc-web-6.0.0-rhel7_x86_64.zip" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/495851/product_files/522039/download
wget -O "pivotal_greenplum_backup_restore-1.15.0-1-gp6-rhel-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb-backup-restore/releases/491475/product_files/516814/download
cd ..
docker build  --build-arg VER=6.1.0 -t greenplum-mne:6.1.0 .
docker tag greenplum-mne:6.1.0 smartivo.azurecr.io/greenplum-mne:6.1.0
