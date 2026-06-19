FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml ./pyproject.toml
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -i https://pypi.org/simple -r requirements.txt

COPY app ./app

COPY alembic ./alembic
COPY alembic.ini ./alembic.ini

EXPOSE 8000

CMD ["sh", "-c", "alembic upgrade head && fastapi dev app/main.py --host 0.0.0.0 --port 8000"]
