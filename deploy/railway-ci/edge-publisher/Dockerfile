FROM public.ecr.aws/docker/library/node:24-bookworm-slim@sha256:2fe369e969550cde8e867afc3fe370b260140cab4a23d467074295b42163d553 AS node
FROM public.ecr.aws/docker/library/python:3.12-slim-bookworm@sha256:782412e85d0f0984994c290652577d4018aff08145c85b262bb63dc0c7522254
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
