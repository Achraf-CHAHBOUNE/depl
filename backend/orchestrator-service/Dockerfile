FROM python:3.10-slim



WORKDIR /app



# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*



# Install dependencies

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt



# Copy application

COPY . .



# Create storage directory

RUN mkdir -p /app/storage/uploads



EXPOSE 8005



CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8005", "--reload"]