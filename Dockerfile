# Playwright Docker: install deps then playwright install --with-deps (per Playwright docs)
FROM python:3.12-bookworm

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && \
    playwright install --with-deps chromium

COPY . .

EXPOSE 5000
ENV PORT=5000

CMD ["python", "app.py"]
