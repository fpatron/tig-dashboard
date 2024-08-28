FROM grafana/alloy:latest
ARG PROMETHEUS_URL

ADD https://raw.githubusercontent.com/fpatron/tig-dashboard/docker/alloy/config_docker.alloy /etc/alloy/config.alloy

RUN   sed -i "s|<PROMETHEUS_ENDPOINT>|${PROMETHEUS_URL}|g" /etc/alloy/config.alloy
RUN   sed -i "s|<PROMETHEUS_PASSWORD>||g" /etc/alloy/config.alloy
RUN   sed -i "s|<PROMETHEUS_USERNAME>||g" /etc/alloy/config.alloy

CMD ["run", "--server.http.listen-addr=0.0.0.0:12345", "--storage.path=/var/lib/alloy/data", "/etc/alloy/config.alloy"]
