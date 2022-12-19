#!/usr/bin/env bash

echo  "Waiting for website to be reachable..."
COUNT=0
MAX=100
SLEEP_TIME=10
ERR=0

if [[ -z "${USER_COUNT}" ]]; then
  LOCUST_COUNT=10
else
  LOCUST_COUNT="${USER_COUNT}"
fi

# Keep checking for haproxy to give proper 401 return to login
until [ "$(curl --write-out %{http_code} --silent --output /dev/null {{ hostvars[haproxy_app]['guest.ipAddress'] }})" -eq "401" ]; do
    sleep ${SLEEP_TIME}
    let "COUNT++"
    echo ${COUNT}
    if [ ${COUNT} -gt ${MAX} ]; then
        ERR=1
        break
    fi
done
if [ ${ERR} -ne 0 ]; then
    echo "Failed to get proper response from haproxy, so guessing something is wrong."
    exit 1
fi

nohup /home/ansible/siwapp/bin/python3 /home/ansible/siwapp/bin/locust --locustfile=/usr/share/systemd/siwapp-locust-file.py --host=http://{{ hostvars[haproxy_app]['guest.ipAddress'] }} &>/dev/null &
sleep 5
nohup curl -X POST -F "user_count=${LOCUST_COUNT}" -F "swarm_rate=10" http://localhost:8089/swarm &>/dev/null &
while :
do
    true
done
