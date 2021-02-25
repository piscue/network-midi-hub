FROM python:3.8.6-alpine
RUN apk add --no-cache --virtual .build-deps \
    build-base \
    alsa-lib-dev
ADD requirements.txt /
RUN pip install -r /requirements.txt \
 && rm /requirements.txt \
 && mkdir -p /app
ADD main.py /app
WORKDIR /app
HEALTHCHECK CMD ["/usr/bin/python", "-V"]
ENTRYPOINT ["python", "/app/main.py"]
