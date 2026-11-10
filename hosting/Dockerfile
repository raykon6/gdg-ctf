# Build context = the gdg-ctf folder:   docker build -f hosting/Dockerfile -t gdg-ctf .
FROM python:3.12-slim
RUN useradd -m ctf
WORKDIR /srv/gdg-ctf
# only what the server needs: data, server, player files, the pcap
COPY hosting/server.py hosting/server.py
COPY hosting/data hosting/data
COPY beginner-kestrel-point/dist beginner-kestrel-point/dist
COPY advanced-chakravyuh/dist advanced-chakravyuh/dist
COPY advanced-chakravyuh/drive advanced-chakravyuh/drive
USER ctf
ENV HOST=0.0.0.0 PORT=8080 PYTHONUNBUFFERED=1
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8080/healthz')"
CMD ["python", "hosting/server.py"]
