#!/bin/bash -x

airflow db migrate

airflow users create \
    --role "Admin" \
    --username "admin" \
    --password "admin" \
    --email "admin@example.com" \
    --firstname "admin" \
    --lastname "user"

airflow variables import "airflow-variables.json"

airflow connections delete aws_default || true
airflow connections add "aws_default" \
    --conn-type "aws" \
    --conn-extra "{\"region_name\": \"${AWS_REGION:-us-east-1}\"}"

airflow webserver -p 8080 &
airflow scheduler &
tail -f /dev/null
