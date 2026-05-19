FROM python:3.11-alpine
WORKDIR /app
COPY . /app
RUN pip install .
ENV SABNZBD_URL=http://host.docker.internal:8080
CMD ["sabnzbd-mcp"]
