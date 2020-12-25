ARG BUILD_FROM
FROM $BUILD_FROM

COPY requirements.txt ./

RUN pip3 install -r requirements.txt
WORKDIR /app
COPY noolite ./noolite
COPY logger ./logger
COPY config ./config
COPY main.py ./

CMD "python3 main.py"
