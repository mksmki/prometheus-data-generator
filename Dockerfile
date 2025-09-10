FROM python:3.13-slim-bookworm


RUN useradd --create-home appuser
USER appuser
WORKDIR /home/appuser

# Don't be confused here, actual copy filter is done in .dockerignore
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD [ "python", "./app/prometheus_data_generator/main.py" ]
