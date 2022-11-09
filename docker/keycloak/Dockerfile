FROM quay.io/keycloak/keycloak:20.0.3

COPY ./import/*.json /opt/keycloak/data/import/

RUN /opt/keycloak/bin/kc.sh import --dir /opt/keycloak/data/import

ENV ROOT_LOGLEVEL=ALL
ENV KEYCLOAK_LOGLEVEL=ALL

CMD ["start-dev"]