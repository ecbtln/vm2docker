#!/bin/bash
docker rm $(docker ps -a -q)
docker rmi $(docker images | grep "^<none>" | awk '{print $"3"}')
rm -rf /tmp/tmp*
df -h
