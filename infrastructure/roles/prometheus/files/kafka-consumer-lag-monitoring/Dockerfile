FROM java:8
WORKDIR /
ADD kafka-consumer-lag-monitoring.jar kafka-consumer-lag-monitoring.jar
ENV KAFKA_SERVER="kafka:9092"
ENV KAFKA_GROUP="kafka2pg"
EXPOSE 9999
CMD java -jar kafka-consumer-lag-monitoring.jar -b ${KAFKA_SERVER} -c ${KAFKA_GROUP} -m "prometheus" -i 5000 -p 9999
