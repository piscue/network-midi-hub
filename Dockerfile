FROM python:3.15
RUN mkdir -p /app
ADD server.py /app
WORKDIR /app
HEALTHCHECK CMD ["python", "-V"]
ENTRYPOINT ["python", "/app/server.py"]
