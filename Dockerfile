FROM ubuntu:12.10

RUN apt-get install -y python-pip
RUN pip install docker-py
RUN apt-get install -y build-essential libfuse-dev subversion
RUN svn co http://www.virtualbox.org/svn/vbox/trunk/include/


ADD . /src/