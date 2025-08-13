# prep stage
FROM python:3.12-slim as builder

WORKDIR /app

# Keeps Python from generating .pyc files in the container
ENV PYTHONDONTWRITEBYTECODE=1

# Turns off buffering for easier container logging
ENV PYTHONUNBUFFERED=1

RUN apt-get update

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /app/wheels -r requirements.txt

# Create a volume
VOLUME /data/vmb

# final stage
FROM python:3.12-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
COPY --from=builder /app/requirements.txt .

# Install pip requirements
RUN pip install --upgrade pip
RUN pip install --no-cache /wheels/*

COPY . /usr/src/app
WORKDIR /usr/src/app

# run docker-entrypoint.sh
RUN chmod +x docker-entrypoint.sh
ENTRYPOINT ["./docker-entrypoint.sh"]

#RUN addgroup --gid 990 --system app && \
#    adduser --no-create-home --shell /bin/false --disabled-password --uid 990 --system --group app

#USER app

CMD ["./my-budget/manage.py", "runserver", "0.0.0.0:8003"]
