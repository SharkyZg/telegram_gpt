# Start with the Amazon Linux base image
FROM public.ecr.aws/lambda/python:3.9

# Set environment variables for Python version and working directory
ENV LANG=C.UTF-8
ENV PYTHON_VERSION=3.9

# Install dependencies
RUN yum update -y && \
    yum install -y python3 python3-pip zip && \
    yum clean all

# Copy the necessary files (your code, requirements.txt, etc.)
COPY ./main.py .
COPY ./requirements.txt .

# Install Python dependencies from the requirements.txt file
RUN pip3 install -r requirements.txt

RUN chmod -R 755 /var
RUN chmod -R 755 /var/task
RUN chmod +x /var/task/main.py
