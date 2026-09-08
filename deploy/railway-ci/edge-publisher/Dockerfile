FROM node:24-bookworm-slim AS node
FROM python:3.12-slim-bookworm
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=node /usr/local/lib/node_modules /usr/local/lib/node_modules
RUN ln -s /usr/local/lib/node_modules/npm/bin/npm-cli.js /usr/local/bin/npm \
    && ln -s /usr/local/lib/node_modules/npm/bin/npx-cli.js /usr/local/bin/npx \
    && apt-get update && apt-get install -y --no-install-recommends \
       git openssh-client ca-certificates tini util-linux procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 10001 --create-home builder
COPY . /controller/
WORKDIR /controller
RUN /usr/bin/tini -s -- python -m unittest test_publish -v
ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["timeout", "--signal=TERM", "--kill-after=30", "1500", "python", "-I", "-S", "/controller/entry.py"]
