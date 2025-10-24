FROM python:3.12-slim

WORKDIR /app

# Copy all backend scripts
COPY *.py /app/

# Make scripts executable
RUN chmod +x /app/*.py

# Expose port
EXPOSE 8080

# Default command (can be overridden)
CMD ["python", "-u", "/app/stable.py"]
