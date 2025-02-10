FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsm6 \
    libxext6 \
    python3-tk \
    portaudio19-dev \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Set the working directory in the container
WORKDIR /app

# Copy the requirements and install them
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copy the Python app into the container
COPY app.py .

# Set display environment variable for Tkinter
ENV DISPLAY=:0

# Expose the port Gradio uses (default is 7860)
EXPOSE 7860

# Run the application
CMD ["python", "app.py"]
