ARG BUILD_FROM
FROM $BUILD_FROM
# FROM arm64v8/python:3.8-slim

COPY requirements.txt ./
# apk add --no-cache build-base \
# && apk remove build-base

# RUN apk update \
#     && apk add --no-cache build-base \
#     && pip3 install --no-cache -r requirements.txt \
#     && apk del build-base
RUN pip3 install --no-cache -r requirements.txt
WORKDIR /app
COPY noolite ./noolite
COPY logger ./logger
COPY config ./config
COPY main.py ./

CMD [ "python3", "main.py" ]
