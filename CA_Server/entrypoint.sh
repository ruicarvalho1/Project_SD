#!/bin/sh

echo "Waiting for database to be ready..."


sleep 2

echo "Running makemigrations..."
python manage.py makemigrations --noinput

echo "Running migrate..."
python manage.py migrate --noinput

echo "Starting Django server..."
python manage.py runserver 0.0.0.0:8000
