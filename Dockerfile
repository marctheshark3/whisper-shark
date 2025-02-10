FROM python:3.9-slim

# Install system dependencies (e.g., ffmpeg is needed by Whisper)
RUN apt-get update && apt-get install -y ffmpeg libsm6 libxext6 && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the Python app into the container
COPY app.py .

# Expose the port Gradio uses (default is 7860)
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
