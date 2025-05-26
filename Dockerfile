FROM python:3.11-slim-bullseye
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV FLASK_APP=quotescom.web:app 
ENV FLASK_ENV=production       

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./src/ /app/src/
COPY pyproject.toml .
COPY README.md .
COPY MANIFEST.in .


RUN pip install --no-cache-dir .

EXPOSE 8080

CMD ["waitress-serve", "--host=0.0.0.0", "--port=8080", "quotescom.web:app"]
