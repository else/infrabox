FROM docker:1.12.6-dind

RUN apk add --no-cache git \
    python \
    py-pip \
    py-psycopg2 \
    py-requests \
    postgresql-client \
    bash \
    iptables \
    pigz \
    openssh-client && \
    pip install docker-compose docker future && \
    apk del py-pip

COPY src/job /job

COPY src/job/ecr_login.sh /usr/local/bin/
COPY src/job/get_compose_exit_code.sh /usr/local/bin/
COPY src/job/entrypoint.sh /usr/local/bin/
COPY src/job/analyze.py /usr/local/bin/
COPY src/utils/wait-for-webserver.sh /usr/local/bin/
COPY src/pyinfrabox /pyinfrabox

ENV PYTHONPATH=/utils:/
ENV PATH=/utils:$PATH

RUN chmod +x /usr/local/bin/wait-for-webserver.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
