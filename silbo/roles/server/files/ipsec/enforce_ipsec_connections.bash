#!/usr/bin/env bash

SLACK_TOKEN=""
if [ $# -gt 0 ]; then
    SLACK_TOKEN=$1
fi

if [ $# -gt 1 ]; then
    echo "Usage : $0 [SLACK_TOKEN]"
    echo "Example : $0"
    exit 1
fi

# get the list of tunnels
if [ -f /etc/smartivo/ipsec/tunnels ]; then
    TUNNELS=`cat /etc/smartivo/ipsec/tunnels`
else
    exit 0
fi

# check server is main server
if [ -e /etc/smartivo/main-server ]; then
    MAIN_SERVER=1
else
    MAIN_SERVER=0
fi

function send_slack_message() {
    curl -G --data-urlencode "channel=#bot" --data-urlencode "as_user=true" --data-urlencode "text=$1" --data-urlencode "token=$SLACK_TOKEN" https://slack.com/api/chat.postMessage
}

function log_message() {
    echo $1
    send_slack_message "$1"
}

# for each tunnel check the status and chang it accordingly
for TUNNEL in $TUNNELS ; do
    TUNNEL_STATUS=`/usr/sbin/ipsec stroke status $TUNNEL | grep $TUNNEL | grep ESTABLISHED | wc -l`
    if [ $TUNNEL_STATUS -eq 0 ] && [ $MAIN_SERVER -eq 1 ]; then
        # start the tunnel
        /usr/sbin/ipsec stroke up-nb $TUNNEL

        # send notification if token is available
        log_message "[$HOSTNAME] Tunnel $TUNNEL turned ON."
    elif [ $TUNNEL_STATUS -ne 0 ] && [ $MAIN_SERVER -eq 0 ]; then
        # disconnect the tunnel
        /usr/sbin/ipsec stroke down-nb $TUNNEL

        # send notification if token is available
        log_message "[$HOSTNAME] Tunnel $TUNNEL turned OFF."
    fi
done


