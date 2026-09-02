FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

ENV ANTLR_VERSION=4.13.1
RUN curl -fsSL -o /usr/local/lib/antlr.jar \
    https://www.antlr.org/download/antlr-${ANTLR_VERSION}-complete.jar

RUN printf '#!/bin/sh\nexec java -jar /usr/local/lib/antlr.jar "$@"\n' > /usr/local/bin/antlr \
    && chmod +x /usr/local/bin/antlr

RUN pip install --no-cache-dir antlr4-python3-runtime==${ANTLR_VERSION} pytest

WORKDIR /program

CMD ["/bin/bash"]
