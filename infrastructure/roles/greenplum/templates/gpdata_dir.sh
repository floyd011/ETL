#!/bin/bash
gpssh -f listhost -e 'sudo mkdir -p /var/lib/gpdb/data'
gpssh -f listhost -e 'sudo mkdir /var/lib/gpdb/data/primary'
gpssh -f listhost -e 'sudo mkdir /var/lib/gpdb/data/gpmaster'
{% if gp_data_directory_mirror is defined %}
gpssh -f listhost -e 'sudo mkdir /var/lib/gpdb/data/mirror'
{% endif %}
gpssh -f listhost -e 'sudo chown -R gpadmin:gpadmin /var/lib/gpdb'
