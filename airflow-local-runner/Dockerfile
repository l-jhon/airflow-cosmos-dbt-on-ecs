FROM apache/airflow:2.8.1

WORKDIR /opt/airflow

USER airflow

COPY requirements.txt requirements.txt
RUN python3 -m pip install --no-cache-dir --retries 5 --timeout 60 -r requirements.txt

ADD config/airflow-variables.json .
ADD config/init.sh .

ENV PIP_USER=false

RUN python3 -m venv dbt_venv && source dbt_venv/bin/activate && \
    python3 -m pip install --no-cache-dir --retries 5 --timeout 60 dbt-athena-community==1.8.4 && deactivate
