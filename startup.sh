#!/bin/bash
# Install Perl and CPANminus
apt-get update
apt-get install -y perl cpanminus

# Install Image::ExifTool module
cpanm Image::ExifTool

# Run the application
uvicorn just:api --host 0.0.0.0 --port 8000
