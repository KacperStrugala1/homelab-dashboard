#image download
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1

#run - bash commands
WORKDIR /app

#download requirements
COPY requirements.txt /app/
RUN pip install -r requirements.txt

#copy all project
COPY . /app/

EXPOSE 8080

#command line commands

CMD [ "python", "/app/homelab_dashboard/manage.py", "makemigrations", "python", "/app/homelab_dashboard/manage.py", "migrate", "python", "/app/homelab_dashboard/manage.py", "runserver", "0.0.0.0:8080"]