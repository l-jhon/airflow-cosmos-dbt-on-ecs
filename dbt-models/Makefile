SHELL := /bin/bash

ENV ?= dev
PROJECT_NAME ?= airflow-cosmos-dbt-on-ecs
AWS_REGION ?= us-east-1
AWS_ACCOUNT_ID ?=
ECR_REPOSITORY ?= ${PROJECT_NAME}-${ENV}
DOCKER_IMAGE_NAME ?= ${ECR_REPOSITORY}
ECR_URI ?= ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPOSITORY}

build_image:
	docker build --platform=linux/amd64 --build-arg ENV=${ENV} -t ${DOCKER_IMAGE_NAME} .

login_ecr_docker_registry:
	test -n "${AWS_ACCOUNT_ID}"
	aws ecr get-login-password --region ${AWS_REGION} | docker login --username AWS --password-stdin ${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com

create_ecr_repository:
	aws ecr create-repository --repository-name ${ECR_REPOSITORY} --image-tag-mutability MUTABLE --image-scanning-configuration scanOnPush=true

build_and_push_docker_image:
	test -n "${AWS_ACCOUNT_ID}"
	docker build --platform=linux/amd64 --build-arg ENV=${ENV} -t ${DOCKER_IMAGE_NAME} .
	docker tag ${DOCKER_IMAGE_NAME}:latest ${ECR_URI}:latest
	docker push ${ECR_URI}:latest

generate_demo_dag:
	python dbt_dag_factory.py

setup_airflow_locally:
	cd ../airflow-local-runner && docker-compose up -d

cleanup_airflow_locally:
	cd ../airflow-local-runner && docker-compose down -v
