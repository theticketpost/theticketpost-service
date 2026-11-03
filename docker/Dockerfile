# theticketpost-service
#
# Build from the repository root:
#   docker build -f docker/Dockerfile -t theticketpost-service .
#
# Run (state in a named volume, UI at http://localhost:8080):
#   docker run -d --name theticketpost -p 8080:8080 -v theticketpost-data:/data theticketpost-service
#
# See docker/README.md for Bluetooth printing and loading apps from a local folder.

FROM python:3.13-slim

# chromium: renders the ticket (pyppeteer uses the system browser, also on ARM)
# fonts:    the ticket is a screenshot, without fonts the text renders as boxes
# tini:     PID 1 that forwards signals, so `docker stop` doesn't wait 10s
# tzdata:   the scheduler prints at local times (set TZ when running)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        chromium \
        fonts-dejavu-core \
        fonts-liberation \
        fonts-noto-color-emoji \
        tini \
        tzdata \
    && rm -rf /var/lib/apt/lists/*

# Non-root user. The virtualenv belongs to it because apps pip-install
# their requirements at runtime. Settings, installed apps and logs live in
# ~/.theticketpost, which points to the /data volume.
RUN useradd --create-home --uid 1000 ttp \
    && python -m venv /opt/venv \
    && mkdir -p /data \
    && ln -s /data /home/ttp/.theticketpost \
    && chown -R ttp:ttp /opt/venv /data

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/home/ttp

USER ttp
WORKDIR /home/ttp/src

COPY --chown=ttp:ttp setup.py pyproject.toml MANIFEST.in README.md ./
COPY --chown=ttp:ttp theticketpost ./theticketpost
RUN pip install . && rm -rf build *.egg-info

VOLUME ["/data"]

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/api/apps/installed', timeout=4)"

ENTRYPOINT ["tini", "--"]
CMD ["theticketpost-service"]
