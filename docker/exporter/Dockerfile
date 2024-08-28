FROM python:3.11-slim
ARG PLAYER_IDS
ARG INNOVATOR_IDS

ENV PLAYER_IDS=$PLAYER_IDS
ENV INNOVATOR_IDS=$INNOVATOR_IDS

WORKDIR /app

ADD https://raw.githubusercontent.com/fpatron/tig-dashboard/docker/exporter/tig_exporter.py /app/tig_exporter.py
ADD https://raw.githubusercontent.com/fpatron/tig-dashboard/docker/exporter/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

CMD ["sh", "-c", "python tig_exporter.py $PLAYER_IDS $INNOVATOR_IDS"]
