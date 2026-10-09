FROM python:3.12-slim
WORKDIR /app
COPY flare-control/control_proxy.py /app/control_proxy.py
USER 10001:10001
EXPOSE 8191
CMD ["python", "-u", "/app/control_proxy.py"]
