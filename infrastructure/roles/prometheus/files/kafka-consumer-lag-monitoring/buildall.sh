#!/bin/bash
set -e
JAVA_HOME=/usr/lib/jvm/java-11-oracle
mkdir .git
./gradlew clean build
cp build/libs/kafka-consumer-lag-monitoring.jar .
rm -f -r .git 
rm -f -r .gradle
rm -f -r build
