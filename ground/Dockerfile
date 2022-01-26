FROM python:3.9

RUN git clone https://github.com/morzack/aerpawlib-vehicle-control.git aerpawlib
WORKDIR aerpawlib
RUN python -m pip install -e .

COPY . /usr/src/app
WORKDIR /usr/src/app
RUN python -m pip install -r ground/requirements.txt

CMD ["python", "-m", "ground"]
