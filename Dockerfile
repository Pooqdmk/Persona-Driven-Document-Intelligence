# Use a lightweight base image for Python, compatible with AMD64
# For production/hackathons, slim-buster or alpine are good choices.
# slim-buster is often easier for scientific libraries if you encounter issues with Alpine.
FROM --platform=linux/amd64 python:3.9-slim-buster

# Set the working directory inside the container
WORKDIR /app

# Copy requirements.txt first to leverage Docker's cache.
# If requirements.txt doesn't change, this layer won't be rebuilt.
COPY requirements.txt .

# Install Python dependencies
# --no-cache-dir to keep image size small
# -r requirements.txt to install from the file
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
# This includes main.py and any other Python files/folders you create (e.g., src/)
COPY . .

# Create input and output directories if they don't exist (important for volume mounts)
# These directories will be mounted by the host, but ensuring they exist prevents issues
RUN mkdir -p input output

# Command to run your application when the container starts
# This matches the expected execution command given in the hackathon brief.
# It tells Python to run main.py
CMD ["python", "main.py"]

# Optional: Expose ports if your Round 2 webapp will run in this container (not needed for Round 1)
# EXPOSE 8080