FROM python:3.12.7-slim

WORKDIR /app

# Dependencies install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy code
COPY . .

# Create directories
RUN mkdir -p database uploads

# Run bot
CMD ["python", "main.py"]
```

**`.dockerignore`** yarating:
```
.venv
venv
__pycache__
*.pyc
.git
.env
*.db
uploads/