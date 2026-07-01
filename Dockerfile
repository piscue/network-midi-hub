FROM python:3.14
RUN mkdir -p /app
ADD server.py /app
WORKDIR /app
HEALTHCHECK CMD ["python", "-V"]
ENTRYPOINT ["python", "/app/server.py"]
