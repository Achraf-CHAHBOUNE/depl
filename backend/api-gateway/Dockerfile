FROM python:3.10-slim



WORKDIR /app



# Install system dependencies including curl for health checks
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*



# Install dependencies

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt



# Copy the entire app directory

COPY app ./app



EXPOSE 8000



# Run the app using the correct module path

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]