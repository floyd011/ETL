Build

ansible-playbook -c local --tags "build" zookeeper.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" kafka.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" connect.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" confluent.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" consul.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" graylog.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" gp.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "build" prometheus.yml --ask-become-pass -e "destination_hosts=localhost"

Push

ansible-playbook -c local --tags "push_images" zookeeper.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" kafka.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" connect.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" confluent.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" consul.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" graylog.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" gp.yml --ask-become-pass -e "destination_hosts=localhost"
ansible-playbook -c local --tags "push_images" prometheus.yml --ask-become-pass -e "destination_hosts=localhost"

Pull

ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" zookeeper.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" kafka.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" connect.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" confluent.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" consul.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server1 --tags "pull_images" graylog.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "pull_images" gp.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server1 --tags "pull_images" prometheus.yml --ask-become-pass -e "destination_hosts=all"

Setup

ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "setup_cluster" zookeeper.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "setup_cluster" kafka.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "setup_cluster" connect.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "setup_cluster" confluent.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4,server3,server1 --tags "setup_cluster" consul.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server1 --tags "setup_cluster" graylog.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server4 --tags "setup_cluster" gp.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server3 --tags "setup_cluster" gp.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server1 --tags "setup_cluster" gp.yml --ask-become-pass -e "destination_hosts=all"
ansible-playbook --inventory inventories/normal_inventory34 --limit server1 --tags "setup_cluster" prometheus.yml --ask-become-pass -e "destination_hosts=all"
