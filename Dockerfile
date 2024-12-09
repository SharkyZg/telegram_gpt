FROM python:3.9-slim

# Set environment variables for Python version and working directory
ENV LANG=C.UTF-8
ENV PYTHON_VERSION=3.9

WORKDIR /app

# Copy the necessary files (your code, requirements.txt, etc.)
COPY . .

# Install Python dependencies from the requirements.txt file
RUN pip3 install -r requirements.txt

# Command to run the app
CMD ["python", "app.py"]