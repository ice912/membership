FROM python:3.9-slim

# SQLite3 도구 설치 명령어 추가
RUN apt-get update && apt-get install -y sqlite3 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY . .
RUN pip install fastapi uvicorn "pydantic[email]" python-multipart
CMD ["uvicorn", "membership:app", "--host", "0.0.0.0", "--port", "8000"]


