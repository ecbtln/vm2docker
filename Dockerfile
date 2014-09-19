FROM ubuntu:14.04
RUN apt-get update
RUN apt-get install -y python python-pip python-dev swig
RUN pip install docker-py
RUN pip install networkx
RUN apt-get install -y rsync curl
RUN curl -s https://get.docker.io/ubuntu/ | sh
RUN apt-get install -y gdb # (for debugging)

# add sourcecode
ADD . /src/

# build products
WORKDIR /src/agent
RUN make clean
RUN make

WORKDIR /src/chief
RUN make clean
RUN make

WORKDIR /src/

ENV AGENT_PORT 1024
EXPOSE 1024
