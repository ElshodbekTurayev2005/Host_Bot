# 1. Python image
FROM python:3.10-slim

# 2. Workdir
WORKDIR /app

# 3. Copy project
COPY . /app

# 4. Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Run bot
CMD ["python", "main.py"]
