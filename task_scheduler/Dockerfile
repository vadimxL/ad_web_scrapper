FROM ubuntu:latest
LABEL authors="vadimv"

# Use an official Python runtime as a base image
FROM python:3.12

# Set the working directory in the container
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Specify the command to run your application
CMD ["python3", "app.py"]