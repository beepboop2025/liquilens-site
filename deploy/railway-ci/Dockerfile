FROM node:24-bookworm-slim AS node
FROM python:3.12-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && apt-get update && apt-get install -y --no-install-recommends git tini \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements-ci.txt package.json package-lock.json ./
RUN python3 -m pip install --disable-pip-version-check --no-cache-dir \
      --only-binary=:all: --require-hashes -r requirements-ci.txt \
    && npm ci --ignore-scripts
COPY . /app
ENV LIQUILENS_OFFLINE=1
ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["timeout", "--signal=TERM", "--kill-after=15", "600", "sh", "deploy/railway-ci/run.sh"]
