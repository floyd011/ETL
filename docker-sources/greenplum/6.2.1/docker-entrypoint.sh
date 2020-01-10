#!/bin/bash
sudo /usr/sbin/sshd

m="master"

master_running () {
pid=$(ps aux | grep [g]pmaster | grep -v grep | awk '{print $2}')
if [ -z "$pid" ];
    then 
         return 1
    else 
         return 0
fi;
}

at_sigint() {
  if [[ "$GP_NODE" == "$m" ]]
  then
    echo "Received SIGINT on the master node: stopping the database..."
    gpstop -M immediate -a
    echo "Database has been stopped on the master node".
  fi
  exit 0
}


if [ "$GP_NODE" == "$m" ]

then
     echo 'Node type='$GP_NODE
    if [ ! -d $MASTER_DATA_DIRECTORY ]; then
        echo 'Master directory does not exist. Initializing master from gpinitsystem_reflect.'
        gpssh-exkeys -f listhost
        echo "Key exchange complete"
        ./gpdata_dir.sh
        gpinitsystem -a -h multihost -c gpinitsys  --su_password=gpadmin
        echo "Master node initialized"
        echo "host all all 0.0.0.0/0 md5" >>/var/lib/gpdb/data/gpmaster/gpsne-1/pg_hba.conf
        gpstop -u
        gppkg -i pivotal_greenplum_backup_restore-1.15.0-1-gp6-rhel-x86_64.gppkg
        gppkg -i postgis-2.1.5+pivotal.2-7-gp6-rhel7-x86_64.gppkg
        gppkg -i plr-3.0.3-gp6-rhel7-x86_64.gppkg
        source $GPHOME/greenplum_path.sh
        export PGPORT=5434
        gpstop -r  -a
        psql -p 5434 -c "CREATE DATABASE smartivodb WITH TEMPLATE = template0 ENCODING = 'UTF8'"
        psql -p 5434 -d smartivodb -c "CREATE EXTENSION plr"
        gpperfmon_install --port 5434 --enable --password gpadmin 
        psql -p 5434 -c "CREATE ROLE cc_admin WITH LOGIN PASSWORD 'gpadmin' SUPERUSER CREATEDB;"
        psql -p 5434 -c "CREATE ROLE smartivodb  WITH LOGIN PASSWORD 'password' SUPERUSER CREATEDB;"
        echo "host gpperfmon  cc_admin 0.0.0.0/0  md5" >> /var/lib/gpdb/data/gpmaster/gpsne-1/pg_hba.conf
        gpstop -r -a
        unzip greenplum-cc-web-6.0.0-rhel7_x86_64.zip
        echo "yes 28080 N" | greenplum-cc-web-6.0.0-rhel7_x86_64/./gpccinstall-6.0.0 -c ccconf >/dev/null 2>&1
        source /usr/local/greenplum-db-6.2.1/greenplum-cc-web-6.0.0/gpcc_path.sh
        gpstop -u 
        gpinitstandby -s gp_db_standby -a
    else
        echo 'Master exists. Restarting gpdb.'
        source $GPHOME/greenplum_path.sh
        gpstart -a
        source /usr/local/greenplum-db-6.2.1/greenplum-cc-web-6.0.0/gpcc_path.sh
    fi
    
    gpcc start    
    gpstate -f
    pid=$(ps aux | grep [g]pmaster | grep -v grep | awk '{print $2}')
    echo $pid
    trap at_sigint INT
    while :
    do
        sleep 1
        master_running
        if [ $? -eq "1" ];
        then 
          if [ "$GP_NODE" == "master" ]
          then        
              ssh gpadmin@gp_db_standby  "/usr/local/bin/./activatemasteronstandby.sh"
              break
          fi
        fi
    done
else
    echo 'Node type='$GP_NODE
    source $GPHOME/greenplum_path.sh
fi

exec "$@"
