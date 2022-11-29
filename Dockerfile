FROM python:3.8.6
ADD requirements.txt /
RUN pip install -r /requirements.txt \
 && rm /requirements.txt \
 && mkdir -p /app
ADD server.py /app
WORKDIR /app
HEALTHCHECK CMD ["/usr/bin/python", "-V"]
ENTRYPOINT ["python", "/app/server.py"]
