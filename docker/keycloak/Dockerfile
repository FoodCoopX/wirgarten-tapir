FROM quay.io/keycloak/keycloak:21.0.2

COPY ./import/*.json /opt/keycloak/data/import/

RUN /opt/keycloak/bin/kc.sh import --dir /opt/keycloak/data/import

ENV ROOT_LOGLEVEL=ALL
ENV KEYCLOAK_LOGLEVEL=ALL

CMD ["start-dev"]