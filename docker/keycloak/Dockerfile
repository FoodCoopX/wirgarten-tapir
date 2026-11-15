FROM quay.io/keycloak/keycloak:26.8.0

COPY ./import/*.json /opt/keycloak/data/import/

# Pre-create the H2 directory so the keycloak-data volume is owned by the keycloak user
RUN mkdir -p /opt/keycloak/data/h2

ENV ROOT_LOGLEVEL=ALL
ENV KEYCLOAK_LOGLEVEL=ALL

CMD ["start-dev", "--import-realm"]
