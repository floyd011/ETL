FROM centos:latest

ARG VER=0.0.0

COPY ${VER}/*.rpm  .

RUN yum install -y epel-release unzip which tar more util-linux-ng passwd openssh-clients openssh-server ed m4 net-tools iproute less vim sudo nano mc apr apr-util zip rsync libevent libyaml openssl bzip2 krb5-devel; yum clean all && \
    rpm -Uvh ./greenplum-db-${VER}-rhel7-x86_64.rpm 
    
RUN yum install -y htop nc R; yum clean all

WORKDIR /inst_scripts
RUN chmod u+s /bin/su
ADD ${VER}/gpadmin_user.sh .
RUN chmod 755 gpadmin_user.sh
RUN ./gpadmin_user.sh
RUN usermod -aG wheel gpadmin

RUN chown -R gpadmin:gpadmin /usr/local/greenplum-db-${VER}

RUN localedef -c -f UTF-8 -i en_US en_US.UTF-8
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8 

WORKDIR /var/lib/gpdb/setup/

COPY ${VER}/*.gppkg /var/lib/gpdb/setup/

COPY ${VER}/*.zip /var/lib/gpdb/setup/

ADD ${VER}/ccconf .
COPY ${VER}/multihost .
COPY ${VER}/listhost .
COPY ${VER}/gpinitsys .
COPY ${VER}/gpdata_dir.sh .

ENV USER=gpadmin
ENV MASTER_DATA_DIRECTORY=/var/lib/gpdb/data/gpmaster/gpsne-1
ADD ${VER}/activatemasteronstandby.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/activatemasteronstandby.sh
ADD ${VER}/docker-entrypoint.sh /usr/local/bin/
RUN chmod 755 /usr/local/bin/docker-entrypoint.sh

RUN chown -R gpadmin:gpadmin /var/lib/gpdb

RUN echo 'gpadmin ALL=(ALL) NOPASSWD:ALL ' >> /etc/sudoers

USER gpadmin

ENV GPHOME=/usr/local/greenplum-db-${VER}
ENV PATH=$GPHOME/bin:$PATH
ENV PYTHONPATH=$GPHOME/lib/python
ENV LD_LIBRARY_PATH=$GPHOME/lib:$LD_LIBRARY_PATH
ENV OPENSSL_CONF=$GPHOME/etc/openssl.cnf
ENV GP_NODE=master

ENV PGPASSWORD=gpadmin
ENV PGPORT=5432

VOLUME /var/lib/gpdb/
ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 5432

CMD ["./monitor_master.sh"]
