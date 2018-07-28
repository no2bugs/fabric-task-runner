#!/bin/bash

echo "STARTED"
uname -o
uname -r
df -h / | tail -n1 | awk '{print $5}'
echo "FINISHED"
sleep 10

