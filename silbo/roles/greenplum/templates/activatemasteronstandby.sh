#!/bin/bash
set -e
export MASTER_DATA_DIRECTORY=/var/lib/gpdb/data/gpmaster/gpsne-1
export PGPORT={{ gp_port }}
source /usr/local/greenplum-db-{{ gp_docker_tag }}/greenplum_path.sh
gpactivatestandby -a
ssh gpadmin@gp_db_master  "cp -fr /var/lib/gpdb/data/gpmaster/gpsne-1 /var/lib/gpdb/setup/"
ssh gpadmin@gp_db_master  "rm -fr /var/lib/gpdb/data/gpmaster/gpsne-1 "
gpinitstandby -s gp_db_master -a
gpstate -f
echo "Greenplum master is activated on node gp_db_standby and standby on gp_db_master"
