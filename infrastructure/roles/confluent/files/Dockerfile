FROM python:alpine3.8
COPY . /app
WORKDIR /app

ENV CONSUL_SERVER=""
ENV CONSUL_PORT=8500
ENV DBSOURCE=""
ENV PYTHONIOENCODING="utf-8"

RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories
RUN sed -i -e 's/v3\.4/edge/g' /etc/apk/repositories \
    && apk upgrade --update-cache --available 
    
RUN apk update && apk add --no-cache librdkafka --virtual .build-deps-edge \
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/testing \    
        --repository http://dl-cdn.alpinelinux.org/alpine/edge/main \
        gdal-dev \
        geos-dev \
        postgresql-dev gcc python3-dev musl-dev librdkafka-dev 
RUN pip install --disable-pip-version-check -r requirements.txt
CMD python ./index.py