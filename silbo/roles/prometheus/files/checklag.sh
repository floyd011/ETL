#!/bin/bash
FILE=/root/prometheus/test.status
if [ ! -f "$FILE" ]; then
    echo "0" > /root/prometheus/test.status
fi
rm -f /root/prometheus/test
docker run --name=check-lag --network="host" --rm omarsmak/kafka-consumer-lag-monitoring:latest -b kafka:9092 -c "kafka2pg" -m "console" -i 60000 -p 3333 > /root/prometheus/test &
CNT=`docker inspect -f '{{.State.Running}}' check-lag 2> /dev/null`
while [ "$CNT" != "true" ]; do
  CNT=`docker inspect -f '{{.State.Running}}' check-lag 2> /dev/null`
done
docker stop check-lag
array=( $(grep -oP '(?<=Total lag: )[0-9]+' /root/prometheus/test) )
for i in "${array[@]}"
do
  if (( $i > 100000 )); then
     read -r -n1 CONFREST < /root/prometheus/test.status
     if [[ "$CONFREST" == 0 ]]; then
        echo "1" > /root/prometheus/test.status
        curl -X POST --data-urlencode "payload={\"channel\": \"@milorad.spasic\", \"username\": \"Kafka-lag\", \"text\": \"This is posted to @milorad.spasic and comes from a bot named Kafka-lag, number is: $i.\", \"icon_emoji\": \":ghost:\"}" https://hooks.slack.com/services/
        /root/./confrest.sh
     fi
     exit
  fi
done
read -r -n1 CONFREST < /root/prometheus/test.status
if [[ "$CONFREST" == 1 ]]; then
    echo "0" > /root/prometheus/test.status
    curl -X POST --data-urlencode "payload={\"channel\": \"@milorad.spasic\", \"username\": \"Kafka-lag\", \"text\": \"This is posted to @milorad.spasic and comes from a bot named Kafka-lag, everything is OK.\", \"icon_emoji\": \":ghost:\"}" https://hooks.slack.com/services/
fi
echo "Not found topic with check-lag"
