# 개발용
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# COPY ./app /app (docker-compose.yml에서 volumes 사용하므로 필요X)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]



# 배포용
# FROM python:3.11
# WORKDIR /app
# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt
# COPY ./app /app
# CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]