FROM node:26-trixie-slim AS base
RUN npm install -g pnpm@12.15.0
# Set working directory
WORKDIR /app

# Install node modules
COPY \
    "./package.json" \
    "./pnpm-lock.yaml" \
    "./pnpm-workspace.yaml" \
    ./
RUN pnpm install

RUN apt-get update -y && apt-get --no-install-recommends install -y default-jre
ENV JAVA_HOME=/usr/lib/jvm/default-java

CMD ["pnpm", "run", "dev"]

# Note: vite.config.js and src code will be mounted via volumes