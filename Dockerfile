FROM ubuntu:12.10

RUN apt-get install -y python python-pip python-dev swig
RUN pip install docker-py
RUN pip install networkx
RUN apt-get install -y rsync curl
RUN curl -s https://get.docker.io/ubuntu/ | sh
ADD . /src/

ENTRYPOINT ["python", "/src/main.py"]