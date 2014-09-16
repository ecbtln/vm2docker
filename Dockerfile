FROM ubuntu:14.04
RUN apt-get update
RUN apt-get install -y python python-pip python-dev swig
RUN pip install docker-py
RUN pip install networkx
RUN apt-get install -y rsync curl
RUN curl -s https://get.docker.io/ubuntu/ | sh
ADD . /src/
WORKDIR /src/chief
RUN make
WORKDIR /src/