#!/bin/bash
# Скрипт имитирующий CI-процесс сборки Docker-образа

# Название и тег образа
IMAGE_NAME="myapp"
IMAGE_TAG="v1.0"

echo "=== Шаг 1: Сборка Docker-образа ==="
docker build -t ${IMAGE_NAME}:${IMAGE_TAG} .

echo "=== Шаг 2: Проверка успешной сборки ==="
docker images | grep ${IMAGE_NAME}

echo "=== Шаг 3: (опционально) Публикация в Docker Hub ==="
# docker login -u <логин> -p <пароль>
# docker tag ${IMAGE_NAME}:${IMAGE_TAG} <логин>/${IMAGE_NAME}:${IMAGE_TAG}
# docker push <логин>/${IMAGE_NAME}:${IMAGE_TAG}

echo "✅ Сборка завершена успешно!"