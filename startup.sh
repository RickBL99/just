#!/bin/bash

# Create a log file we can check
LOG_FILE="/home/LogFiles/startup.log"
echo "========================================" >> $LOG_FILE
echo "Startup script started at $(date)" >> $LOG_FILE

# Install exiftool
echo "Running apt-get update..." >> $LOG_FILE
apt-get update >> $LOG_FILE 2>&1

echo "Installing libimage-exiftool-perl..." >> $LOG_FILE
apt-get install -y libimage-exiftool-perl >> $LOG_FILE 2>&1

# Verify installation
echo "Checking exiftool installation..." >> $LOG_FILE
which exiftool >> $LOG_FILE 2>&1
exiftool -ver >> $LOG_FILE 2>&1

echo "Starting uvicorn at $(date)..." >> $LOG_FILE

# Run the application
uvicorn just:api --host 0.0.0.0 --port 8000