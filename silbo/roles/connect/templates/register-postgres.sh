curl -i --trace-ascii dump.txt -X POST -H "Accept:application/json" -H  "Content-Type:application/json" http://127.0.0.1:8083/connectors/ -d @register-postgres.json
