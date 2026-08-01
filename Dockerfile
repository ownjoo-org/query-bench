# hadolint ignore=DL3006
FROM cgr.dev/chainguard/wolfi-base

# hadolint ignore=DL3018
RUN apk add --no-cache \
        ca-certificates-bundle \
        git \
        python-3.14 \
    && python3.14 -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir "oj-toolkit>=0.2.3" \
    && addgroup -S toolrunner && adduser -S -G toolrunner toolrunner \
    && chown -R toolrunner:toolrunner /opt/venv \
    && mkdir -p /output && chown toolrunner:toolrunner /output

ENV PATH="/opt/venv/bin:${PATH}"

COPY menu.py /usr/local/bin/menu.py
COPY DISCLAIMER.md /usr/local/share/query-bench/DISCLAIMER.md
RUN chmod +x /usr/local/bin/menu.py

USER toolrunner
WORKDIR /home/toolrunner

ENTRYPOINT ["python3.14", "/usr/local/bin/menu.py"]
