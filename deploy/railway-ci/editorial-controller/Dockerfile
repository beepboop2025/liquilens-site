FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates git openssh-client procps tini \
    && rm -rf /var/lib/apt/lists/*
RUN groupadd --gid 65532 editorial-writer \
    && useradd --uid 65532 --gid 65532 --no-create-home --no-log-init \
       --home-dir /nonexistent --shell /usr/sbin/nologin --password '!' editorial-writer
WORKDIR /controller
COPY requirements-ci.txt .
RUN python -m pip install --disable-pip-version-check --no-cache-dir \
    --only-binary=:all: --require-hashes -r requirements-ci.txt
COPY Dockerfile editorial.py isolation.py test_editorial.py github-known-hosts ./
RUN /usr/bin/tini -s -- python test_editorial.py
ENTRYPOINT ["/usr/bin/tini", "-s", "--"]
CMD ["timeout", "--signal=TERM", "--kill-after=30", "1500", "python", "-u", "editorial.py"]
