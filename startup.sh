#!/bin/bash
# Install exiftool via apt (creates the executable)
apt-get update
apt-get install -y libimage-exiftool-perl

# Run the application
uvicorn just:api --host 0.0.0.0 --port 8000