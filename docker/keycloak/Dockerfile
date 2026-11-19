FROM quay.io/keycloak/keycloak:26.8.2

COPY ./import/*.json /opt/keycloak/data/import/

ENV ROOT_LOGLEVEL=ALL
ENV KEYCLOAK_LOGLEVEL=ALL

CMD ["start-dev", "--import-realm"]
