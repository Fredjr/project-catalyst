FROM python:3.9-slim

# Install Nginx
RUN apt-get update && \
    apt-get install -y nginx && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Copy Nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Create startup script
COPY <<-'EOF' /app/start.sh
#!/bin/bash

# Create required Nginx directories
mkdir -p /run/nginx

# Start FastAPI in background
uvicorn api_main:app --host 127.0.0.1 --port 8000 &
FASTAPI_PID=$!

# Wait for FastAPI to start
sleep 5

# Check if FastAPI is running
if ! kill -0 $FASTAPI_PID 2>/dev/null; then
    echo "FastAPI failed to start"
    exit 1
fi

# Start Nginx in foreground
nginx -g "daemon off;"
EOF

RUN chmod +x /app/start.sh

EXPOSE 80

CMD ["/app/start.sh"]
