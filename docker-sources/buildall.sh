#!/bin/bash
set -e
docker build -t java-centos-openjdk11-jdk:latest ./centos-openjdk-11
docker build -t zookeeper:1.0 ./zookeeper
docker build -t kafka:1.0 ./kafka
docker build -t connect-base:1.0 ./connect-base
docker build -t connect:1.0 ./connect
docker build -t consul:1.6.2 ./consul
docker build -t elasticsearch:6.8.6 ./elastic
docker build -t mongo:latest ./mongo
docker build -t graylog:3.1.3 ./graylog
docker build --build-arg PG_VERSION=10.5 -t timescaledb:1.1.1-pg10 ./timescaledb-docker
docker build --build-arg PG_VERSION_TAG=pg10 -t pg_prometheus:latest ./pg_prometheus
docker build -t prometheus-postgresql-adapter:latest ./prometheus-postgresql-adapter
docker build -t prometheus:latest ./prometheus
docker build -t postgres:11.6 ./postgres/11
cd kafka-consumer-lag-monitoring
./buildall.sh
cd greenplum
./buildall.sh
docker tag java-centos-openjdk11-jdk:latest $1/java-centos-openjdk11-jdk:latest
docker tag zookeeper:1.0 $1/zookeeper:1.0
docker tag kafka:1.0 $1/kafka:1.0 
docker tag connect-base:1.0 $1/connect-base:1.0 
docker tag connect:1.0 $1/connect:1.0
docker tag consul:1.6.2 $1/consul:1.6.2
docker tag elasticsearch:6.8.6 $1/elasticsearch:6.8.6
docker tag mongo:latest $1/mongo:latest 
docker tag graylog:3.1.3 $1/graylog:3.1.3
docker tag timescaledb:1.1.1-pg10 $1/timescaledb:1.1.1-pg10
docker tag pg_prometheus:latest $1/pg_prometheus:latest
docker tag prometheus-postgresql-adapter:latest $1/prometheus-postgresql-adapter:latest
docker tag prometheus:latest $1/prometheus:latest
docker tag kafka-lag:latest $1/kafka-lag:latest
docker tag greenplum-mne:6.2.1 $1/greenplum-mne:6.2.1
docker tag postgres:11.6 $1/postgres:11.6


