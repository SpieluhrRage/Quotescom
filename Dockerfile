
FROM python:3.12.1
LABEL Timur Platonov 'gered370@gmail.com'

RUN apt-get update && apt-get -y install python3-pip python3-dev build-essential
COPY . /tfa
WORKDIR /tfa 
RUN pip install -r requirements.txt
EXPOSE 8080
EXPOSE 5000
ENTRYPOINT ["python"]
CMD ["tfa.py"]