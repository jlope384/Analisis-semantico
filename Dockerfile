FROM python:3.11-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends default-jre-headless curl \
    && rm -rf /var/lib/apt/lists/*

ENV ANTLR_VERSION=4.13.1
RUN curl -fsSL -o /usr/local/lib/antlr.jar \
    https://www.antlr.org/download/antlr-${ANTLR_VERSION}-complete.jar

RUN printf '#!/bin/sh\nexec java -jar /usr/local/lib/antlr.jar "$@"\n' > /usr/local/bin/antlr \
    && chmod +x /usr/local/bin/antlr

# Simulador MIPS (MARS) para ejecutar el ensamblador que genera el compilador.
# `mars programa.asm` lo ejecuta en consola, sin interfaz grafica.
ENV MARS_VERSION=4.5.1
RUN curl -fsSL -o /usr/local/lib/Mars4_5.jar \
    https://github.com/dpetersanderson/MARS/releases/download/v.${MARS_VERSION}/Mars4_5.jar

RUN printf '#!/bin/sh\nexec java -Djava.awt.headless=true -jar /usr/local/lib/Mars4_5.jar nc "$@"\n' > /usr/local/bin/mars \
    && chmod +x /usr/local/bin/mars

RUN pip install --no-cache-dir antlr4-python3-runtime==${ANTLR_VERSION} pytest

WORKDIR /program

CMD ["/bin/bash"]
