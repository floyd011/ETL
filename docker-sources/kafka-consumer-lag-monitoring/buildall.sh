#!/bin/bash
set -e
mkdir .git
./gradlew clean build
cp build/libs/kafka-consumer-lag-monitoring.jar .
rm -f -r .git 
rm -f -r .gradle
rm -f -r build
docker build -t kafka-lag:latest .
rm -f kafka-consumer-lag-monitoring.jar
cd ..
