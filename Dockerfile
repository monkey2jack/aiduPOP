FROM python:3.12-slim

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir build && \
    pip install --no-cache-dir .

EXPOSE 8000

CMD ["python3", "-m", "hermes_lark_streaming"]
