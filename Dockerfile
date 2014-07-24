FROM ubuntu:12.10

RUN apt-get install -y python python-pip
RUN pip install docker-py
RUN apt-get install -y rsync curl
RUN curl -s https://get.docker.io/ubuntu/ | sh
ADD . /src/