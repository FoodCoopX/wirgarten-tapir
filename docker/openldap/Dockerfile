FROM osixia/openldap:stable

RUN apt-get update && apt-get install -y \
    curl \
    python3-distutils \
    python3-pip


RUN pip3 install volatildap Flask

RUN mkdir -p /app

COPY ./app /app
