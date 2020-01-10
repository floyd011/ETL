#!/bin/bash
set -e
wget -O "$1/greenplum-db-6.2.1-rhel7-x86_64.rpm" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/526878/product_files/556004/download
wget -O "$1/plr-3.0.3-gp6-rhel7-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/526878/product_files/556011/download
wget -O "$1/postgis-2.1.5+pivotal.2-7-gp6-rhel7-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/526878/product_files/556067/download
wget -O "$1/greenplum-cc-web-6.0.0-rhel7_x86_64.zip" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb/releases/526878/product_files/556059/download
wget -O "$1/pivotal_greenplum_backup_restore-1.15.0-1-gp6-rhel-x86_64.gppkg" --header="Authorization: Token Txp3kHpfsy6BTkeAPA4F" https://network.pivotal.io/api/v2/products/pivotal-gpdb-backup-restore/releases/491475/product_files/516814/download
