ARG ARCH="amd64"
ARG OS="linux"
FROM quay.io/prometheus/busybox-${OS}-${ARCH}:latest
LABEL maintainer="The Prometheus Authors <prometheus-developers@googlegroups.com>"

ARG ARCH="amd64"
ARG OS="linux"
USER       root
RUN \
  mkdir -p /opt/prometheus

RUN wget -q -O /opt/prometheus-2.15.1.linux-amd64.tar.gz https://github.com/prometheus/prometheus/releases/download/v2.15.1/prometheus-2.15.1.linux-amd64.tar.gz
RUN tar --extract --gzip --file /opt/prometheus-2.15.1.linux-amd64.tar.gz --strip-components=1   --directory /opt/prometheus

RUN mkdir -p /usr/share/prometheus/console_libraries

RUN mkdir -p /usr/share/prometheus/consoles

RUN cp /opt/prometheus/prometheus        /bin/prometheus
RUN cp /opt/prometheus/promtool          /bin/promtool
RUN cp -r /opt/prometheus/console_libraries/                     /usr/share/prometheus/console_libraries/
RUN cp -r /opt/prometheus/consoles/                              /usr/share/prometheus/consoles/
RUN cp /opt/prometheus/LICENSE                                /LICENSE
RUN cp /opt/prometheus/NOTICE                                 /NOTICE

RUN mkdir -p /etc/prometheus
RUN ln -s /usr/share/prometheus/console_libraries /usr/share/prometheus/consoles/ /etc/prometheus/
RUN mkdir -p /prometheus && \
    chown -R nobody:nogroup etc/prometheus /prometheus

USER       nobody
EXPOSE     9090
VOLUME     [ "/prometheus" ]
WORKDIR    /prometheus
ENTRYPOINT [ "/bin/prometheus" ]
CMD        [ "--config.file=/etc/prometheus/prometheus.yml", \
             "--storage.tsdb.path=/prometheus", \
             "--web.console.libraries=/usr/share/prometheus/console_libraries", \
             "--web.console.templates=/usr/share/prometheus/consoles" ]

