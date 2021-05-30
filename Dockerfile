FROM ubuntu:focal

ENV REDIS_SRV localhost
ENV YAML_PATH /appdata


RUN apt update -qq && apt install -y python3-pip python3-yaml git && pip3 install asyncio aioredis requests bs4 volkswagencarnet
ADD app/* /app/
WORKDIR /app

CMD ["/usr/bin/python3", "-u", "/app/getstats.py"]
