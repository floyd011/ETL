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
        gpinitsystem -a -h multihost -c gpinitsys  --su_password={{ gp_password }}
        echo "Master node initialized"
        echo "host all all 0.0.0.0/0 md5" >>/var/lib/gpdb/data/gpmaster/gpsne-1/pg_hba.conf
        gpstop -u
        gppkg -i {{ gp_backup }}
        gppkg -i {{ gp_postgis }}
        gppkg -i {{ gp_plr }}
        source $GPHOME/greenplum_path.sh
        export PGPORT={{ gp_port }}
        gpstop -r -a
        psql -p {{ gp_port }} -c "CREATE DATABASE {{ gp_db_name }} WITH TEMPLATE = template0 ENCODING = 'UTF8'"
        psql -p {{ gp_port }} -d {{ gp_db_name }} -c "CREATE EXTENSION plr"
        gpperfmon_install --port {{ gp_port }} --enable --password {{ gp_password }} 
        psql -p {{ gp_port }} -c "CREATE ROLE cc_admin WITH LOGIN PASSWORD '{{ gp_password }}' SUPERUSER CREATEDB;"
        psql -p {{ gp_port }} -c "CREATE ROLE {{ gp_user }}  WITH LOGIN PASSWORD '{{ gpcc_password }}' SUPERUSER CREATEDB;"
        echo "host gpperfmon  cc_admin 0.0.0.0/0  md5" >> /var/lib/gpdb/data/gpmaster/gpsne-1/pg_hba.conf
        gpstop -r -a
        unzip {{ gp_cc }}.zip
        echo "yes {{ gpcc_port }} N" | {{ gp_cc }}/./gpccinstall-{{ gp_cc_ver }} -c ccconf >/dev/null 2>&1
        source /usr/local/greenplum-db-{{ gp_docker_tag }}/greenplum-cc-web-{{ gp_cc_ver }}/gpcc_path.sh
        gpstop -u 
        gpinitstandby -s gp_db_standby -a
    else
        echo 'Master exists. Restarting gpdb.'
        source $GPHOME/greenplum_path.sh
        gpstart -a
        source /usr/local/greenplum-db-{{ gp_docker_tag }}/greenplum-cc-web-{{ gp_cc_ver }}/gpcc_path.sh
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
