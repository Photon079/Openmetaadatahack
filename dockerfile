# Use a stable Python version
FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Install system dependencies (useful for AI/Data science libs)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project into the container
COPY . .

# Run your main agent script (Assuming agent.py is the entry point)
# This starts a bash shell by default instead of running your script
CMD ["/bin/bash"]