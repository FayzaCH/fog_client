#!/bin/bash
docker build --no-cache --tag fog_client:latest .
docker build --no-cache --tag fog_client:containernet --file Dockerfile-containernet . 
#sudo docker build --no-cache --tag fog_client:test --file Dockerfile_test .
docker build --no-cache --tag fog_client:script --file Dockerfile-script .
docker build --no-cache --tag fog_client:containernet-script --file Dockerfile-containernet-script . 