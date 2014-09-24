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
RUN chmod +x vm2docker.py

ENTRYPOINT ["./vm2docker.py"]

ENV DOCKER_HOST tcp://192.168.59.103:2375
#ENV AGENT_PORT 49153
#EXPOSE 49153
