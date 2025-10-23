FROM python:3.12-slim

WORKDIR /app

# Copy backend scripts
COPY stable.py /app/stable.py
COPY canary.py /app/canary.py
COPY primary.py /app/primary.py
COPY shadow.py /app/shadow.py

# Make scripts executable
RUN chmod +x /app/*.py

# Expose port
EXPOSE 8080

# Default command (can be overridden)
CMD ["python", "-u", "/app/stable.py"]
