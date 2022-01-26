FROM python:3.8

RUN git clone https://github.com/morzack/aerpawlib-vehicle-control.git aerpawlib
WORKDIR aerpawlib
RUN python3.8 -m pip install -e .

RUN mkdir /code
COPY . /code
WORKDIR /code
RUN python3.8 -m pip install -r /code/drone/requirements.txt

RUN apt update
RUN apt install -y wget screen net-tools
RUN wget https://raw.githubusercontent.com/vishnubob/wait-for-it/master/wait-for-it.sh
RUN chmod +x wait-for-it.sh

ENV PORT 5770
ENV GROUNDPORT 5761

CMD ./drone/start.sh
