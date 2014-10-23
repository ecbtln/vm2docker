FROM ubuntu:14.04
RUN apt-get update
RUN apt-get install -y python python-pip python-dev swig
RUN pip install docker-py
RUN pip install networkx
RUN apt-get install -y rsync curl duplicity
RUN curl -s https://get.docker.io/builds/Linux/x86_64/docker-latest -o /usr/local/bin/docker
RUN chmod +x /usr/local/bin/docker
RUN apt-get install -y gdb # (for debugging)

# add sourcecode
ADD . /src/

# build products
#WORKDIR /src/agent
#RUN make clean
#RUN make

WORKDIR /src/chief
RUN make clean
RUN make
RUN chmod +x vm2docker.py

ENTRYPOINT ["./vm2docker.py"]

ENV DOCKER_HOST tcp://192.168.59.103:2375
# TODO: experiment with ONBUILD to add code after the fact