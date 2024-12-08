# Use slim Python image instead of AWS Lambda
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose web port
EXPOSE 8080

# Use gunicorn to run the Flask app
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]
