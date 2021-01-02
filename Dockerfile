FROM acaranta/dind-compose:latest

ENV REDIS_SRV localhost
ENV YAML_PATH /appdata


RUN apt update -qq && apt install -y python3-pip && pip3 install asyncio aioredis requests bs4
ADD app/* /app/
WORKDIR /app

CMD ["/usr/bin/python3", "-u", "/app/getstats.py"]
