FROM python:3.13-slim

ENV PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --yes --no-install-recommends tor ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /usr/sbin/nologin torhubgen

WORKDIR /app

RUN pip install --no-cache-dir "stem>=1.8,<2"

COPY torhubgen /app/torhubgen
COPY docs /app/docs
COPY readme.md /app/readme.md

USER torhubgen

# Intentionally no EXPOSE: the local HTTP server stays on 127.0.0.1 and is
# meant to be reached only through the ephemeral onion service.
CMD ["python", "-m", "torhubgen", "--lifetime-seconds", "3600", "--tor-cmd", "tor"]
