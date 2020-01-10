#!/bin/bash
set -e
export MASTER_DATA_DIRECTORY=/var/lib/gpdb/data/gpmaster/gpsne-1
export PGPORT=5434
source /usr/local/greenplum-db-6.2.1/greenplum_path.sh
gpactivatestandby -a
ssh gpadmin@gp_db_master  "cp -fr /var/lib/gpdb/data/gpmaster/gpsne-1 /var/lib/gpdb/setup/"
ssh gpadmin@gp_db_master  "rm -fr /var/lib/gpdb/data/gpmaster/gpsne-1 "
gpinitstandby -s gp_db_master -a
gpstate -f
echo "GPmaster is activated on node gp_db_standby and standby on gp_db_master_1"
