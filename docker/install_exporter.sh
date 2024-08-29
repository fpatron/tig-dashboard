#!/bin/bash
mkdir -p alloy && mkdir -p exporter 
wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/docker/docker-compose-exporter.yml
wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/docker/alloy/Dockerfile -P alloy
wget https://raw.githubusercontent.com/fpatron/tig-dashboard/master/docker/exporter/Dockerfile -P exporter