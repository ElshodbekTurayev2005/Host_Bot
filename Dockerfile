# Use official Python image
FROM python:3.10

# Set work directory
WORKDIR /app

# Copy project files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Run bot
CMD ["python", "main.py"]
