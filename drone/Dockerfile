FROM python:3.8

RUN git clone https://github.com/morzack/aerpawlib-vehicle-control.git aerpawlib
WORKDIR aerpawlib
RUN python3.8 -m pip install -e .

COPY . /usr/app/src
WORKDIR /usr/app/src

ENV PORT 5770

ENTRYPOINT ["python3.8", "-m aerpawlib", "--conn udp:sitl:${PORT}","--vehicle drone", "--script main"]
