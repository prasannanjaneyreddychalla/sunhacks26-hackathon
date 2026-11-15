FROM node:22-bookworm-slim
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv zip jq curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
RUN pip install --no-cache-dir awscli boto3 pytest requests localstack-sdk-python
COPY lstk /usr/local/bin/lstk
COPY tools.sh /opt/lab/tools.sh
COPY deploy_community.py notification_handler.py dlq_relay_handler.py test_community.py /opt/lab/
RUN sed -i 's/\r$//' /usr/local/bin/lstk /opt/lab/tools.sh \
    && chmod +x /usr/local/bin/lstk /opt/lab/tools.sh
WORKDIR /workspace
