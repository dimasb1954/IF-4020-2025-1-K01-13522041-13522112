FROM python:3.11-slim

# Install system dependencies for python-magic and ffmpeg
RUN apt-get update && apt-get install -y \
    libmagic1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /backend
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .

ENV PYTHONPATH=/backend

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]