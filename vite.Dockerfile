FROM node:lts-slim AS base
RUN corepack enable
# Set working directory
WORKDIR /app

# Install node modules
COPY \
    "./package.json" \
    "./pnpm-lock.yaml" \
    ./
RUN pnpm install

RUN apt-get update -y && apt-get --no-install-recommends install -y default-jre
ENV JAVA_HOME /usr/lib/jvm/java-17-openjdk-amd64/

CMD pnpm run dev

# Note: vite.config.js and src code will be mounted via volumes