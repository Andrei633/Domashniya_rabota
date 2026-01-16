#!/usr/bin/env python3
"""
Kubernetes Monitoring Dashboard
Интеграция с проектом мониторинга из репозитория
"""

import os
import yaml
import json
import requests
import subprocess
import psutil
from datetime import datetime
from kubernetes import client, config
from prometheus_api_client import PrometheusConnect


class KubernetesMonitor:
    def __init__(self, namespace="monitoring"):
        self.namespace = namespace
        self.k8s_config = None
        self.prometheus = None

        # Пути к файлам проекта
        self.project_files = {
            'deployment': 'deployment.yaml',
            'service': 'service.yaml',
            'jenkins_script': 'jenkins-build.sh',
            'dockerfile': 'Dockerfile'
        }

    def setup_environment(self):
        """Настройка окружения Kubernetes"""
        try:
            # Проверяем, запущен ли Minikube
            result = subprocess.run(['minikube', 'status'],
                                    capture_output=True, text=True)

            if 'Running' not in result.stdout:
                print("Запуск Minikube...")
                subprocess.run(['minikube', 'start', '--memory=4096', '--cpus=2'],
                               capture_output=True)

            # Загружаем конфигурацию Kubernetes
            config.load_kube_config()
            self.k8s_config = client.Configuration()

            # Подключаемся к Prometheus
            self.connect_prometheus()

            print("✅ Окружение настроено успешно")
            return True

        except Exception as e:
            print(f"❌ Ошибка настройки: {e}")
            return False

    def connect_prometheus(self):
        """Подключение к Prometheus"""
        try:
            # Получаем URL Prometheus
            prometheus_url = self.get_prometheus_url()
            self.prometheus = PrometheusConnect(url=prometheus_url, disable_ssl=True)
            print(f"✅ Подключено к Prometheus: {prometheus_url}")
            return True
        except Exception as e:
            print(f"❌ Ошибка подключения к Prometheus: {e}")
            return False

    def get_prometheus_url(self):
        """Получение URL Prometheus из сервисов"""
        try:
            config.load_kube_config()
            v1 = client.CoreV1Api()

            services = v1.list_namespaced_service(
                namespace=self.namespace,
                label_selector="app=prometheus"
            )

            for svc in services.items:
                if svc.spec.ports:
                    port = svc.spec.ports[0].node_port
                    if port:
                        node_ip = self.get_minikube_ip()
                        return f"http://{node_ip}:{port}"

            return "http://localhost:9090"

        except Exception:
            return "http://localhost:9090"

    def get_minikube_ip(self):
        """Получение IP адреса Minikube"""
        try:
            result = subprocess.run(['minikube', 'ip'],
                                    capture_output=True, text=True)
            return result.stdout.strip()
        except Exception:
            return "192.168.49.2"

    def deploy_application(self):
        """Развертывание приложения из файлов проекта"""
        print("🚀 Развертывание приложения...")

        try:
            # 1. Проверяем и исправляем deployment.yaml
            self.fix_deployment_file()

            # 2. Собираем Docker образ
            print("🔨 Сборка Docker образа...")
            subprocess.run(['docker', 'build', '-t', 'my-docker-app:latest', '.'],
                           capture_output=True)

            # 3. Загружаем образ в Minikube
            print("📦 Загрузка образа в Minikube...")
            subprocess.run(['minikube', 'image', 'load', 'my-docker-app:latest'],
                           capture_output=True)

            # 4. Применяем конфигурации
            print("⚙️ Применение Kubernetes манифестов...")
            subprocess.run(['kubectl', 'apply', '-f', 'deployment.yaml'],
                           capture_output=True)
            subprocess.run(['kubectl', 'apply', '-f', 'service.yaml'],
                           capture_output=True)

            # 5. Проверяем статус
            self.check_deployment_status()

            print("✅ Приложение успешно развернуто!")
            return True

        except Exception as e:
            print(f"❌ Ошибка развертывания: {e}")
            return False

    def fix_deployment_file(self):
        """Исправление deployment.yaml файла"""
        deployment_content = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-docker-app
spec:
  replicas: 1
  selector:
    matchLabels:
      app: my-docker-app
  template:
    metadata:
      labels:
        app: my-docker-app
    spec:
      containers:
      - name: my-docker-app
        image: my-docker-app:latest
        imagePullPolicy: Never
        ports:
        - containerPort: 5000
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"""

        with open('deployment.yaml', 'w') as f:
            f.write(deployment_content)

        print("✅ Файл deployment.yaml исправлен")

    def check_deployment_status(self):
        """Проверка статуса деплоймента"""
        try:
            result = subprocess.run(
                ['kubectl', 'get', 'deployment', 'my-docker-app', '-o', 'json'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                data = json.loads(result.stdout)
                ready = data['status'].get('readyReplicas', 0)
                total = data['spec']['replicas']

                print(f"📊 Статус деплоймента: {ready}/{total} готово")

                if ready == total:
                    print("🎉 Деплоймент готов!")

                    # Получаем URL сервиса
                    service_result = subprocess.run(
                        ['kubectl', 'get', 'svc', 'my-docker-service', '-o', 'json'],
                        capture_output=True, text=True
                    )

                    if service_result.returncode == 0:
                        svc_data = json.loads(service_result.stdout)
                        node_port = svc_data['spec']['ports'][0]['nodePort']
                        ip = self.get_minikube_ip()
                        print(f"🌐 Доступно по адресу: http://{ip}:{node_port}")

                return ready == total
            return False

        except Exception as e:
            print(f"Ошибка проверки статуса: {e}")
            return False

    def get_prometheus_metrics(self):
        """Получение метрик из Prometheus"""
        if not self.prometheus:
            print("⚠️ Prometheus не подключен")
            return {}

        try:
            metrics = {}

            # 1. CPU Usage (как в проекте)
            cpu_query = '100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)'
            cpu_result = self.prometheus.custom_query(cpu_query)
            metrics['cpu'] = cpu_result[0]['value'][1] if cpu_result else "N/A"

            # 2. Memory Usage
            memory_query = '100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))'
            memory_result = self.prometheus.custom_query(memory_query)
            metrics['memory'] = memory_result[0]['value'][1] if memory_result else "N/A"

            # 3. Disk Usage
            disk_query = '100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})'
            disk_result = self.prometheus.custom_query(disk_query)
            metrics['disk'] = disk_result[0]['value'][1] if disk_result else "N/A"

            # 4. Pod статусы
            pods_query = 'kube_pod_status_phase{namespace="monitoring"}'
            pods_result = self.prometheus.custom_query(pods_query)
            metrics['pods'] = len(pods_result) if pods_result else 0

            print(f"📊 Метрики Prometheus:")
            print(f"  CPU: {metrics.get('cpu', 'N/A')}%")
            print(f"  Память: {metrics.get('memory', 'N/A')}%")
            print(f"  Диск: {metrics.get('disk', 'N/A')}%")
            print(f"  Pods в monitoring: {metrics.get('pods', 0)}")

            return metrics

        except Exception as e:
            print(f"❌ Ошибка получения метрик: {e}")
            return {}

    def run_jenkins_build(self):
        """Запуск Jenkins сборки"""
        print("🛠 Запуск Jenkins сборки...")

        try:
            # Проверяем наличие файла
            if not os.path.exists('jenkins-build.sh'):
                print("⚠️ Файл jenkins-build.sh не найден, создаю...")
                self.create_jenkins_script()

            # Делаем файл исполняемым
            os.chmod('jenkins-build.sh', 0o755)

            # Запускаем сборку
            result = subprocess.run(
                ['bash', 'jenkins-build.sh'],
                capture_output=True,
                text=True
            )

            print(result.stdout)
            if result.stderr:
                print(f"⚠️ Предупреждения: {result.stderr}")

            print("✅ Jenkins сборка завершена")
            return result.returncode == 0

        except Exception as e:
            print(f"❌ Ошибка Jenkins сборки: {e}")
            return False

    def create_jenkins_script(self):
        """Создание Jenkins скрипта"""
        script_content = """#!/bin/bash
# Улучшенный скрипт Jenkins сборки

echo "=== Шаг 1: Сборка Docker-образа ==="
docker build -t my-docker-app:latest .

echo "=== Шаг 2: Загрузка в Minikube ==="
minikube image load my-docker-app:latest

echo "=== Шаг 3: Проверка образа ==="
docker images | grep my-docker-app

echo "=== Шаг 4: Развертывание в Kubernetes ==="
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml

echo "=== Шаг 5: Проверка статуса ==="
kubectl get deployment my-docker-app
kubectl get svc my-docker-service

echo "✅ Сборка и развертывание завершены!"
"""

        with open('jenkins-build.sh', 'w') as f:
            f.write(script_content)

    def create_app_py(self):
        """Создание основного приложения"""
        app_content = """from flask import Flask, jsonify
import psutil
import socket
from datetime import datetime

app = Flask(__name__)

@app.route('/')
def home():
    return '''
    <h1>Kubernetes Monitoring App</h1>
    <p>Доступные endpoints:</p>
    <ul>
        <li><a href="/health">/health</a> - Статус приложения</li>
        <li><a href="/metrics">/metrics</a> - Системные метрики</li>
        <li><a href="/info">/info</a> - Информация о системе</li>
    </ul>
    '''

@app.route('/health')
def health():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'hostname': socket.gethostname()
    })

@app.route('/metrics')
def metrics():
    cpu = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')

    return jsonify({
        'cpu_percent': cpu,
        'memory_percent': memory.percent,
        'memory_available_gb': round(memory.available / (1024**3), 2),
        'disk_percent': disk.percent,
        'disk_free_gb': round(disk.free / (1024**3), 2)
    })

@app.route('/info')
def info():
    return jsonify({
        'system': socket.gethostname(),
        'platform': psutil.os.name,
        'python_version': psutil.__version__,
        'cores': psutil.cpu_count(),
        'total_memory_gb': round(psutil.virtual_memory().total / (1024**3), 2)
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
"""

        with open('app.py', 'w') as f:
            f.write(app_content)

        print("✅ Файл app.py создан")

    def create_requirements(self):
        """Создание requirements.txt"""
        requirements = """Flask==2.3.3
psutil==5.9.5
prometheus-api-client==0.5.1
kubernetes==26.1.0
pyyaml==6.0
requests==2.31.0"""

        with open('requirements.txt', 'w') as f:
            f.write(requirements)

        print("✅ Файл requirements.txt создан")

    def dashboard(self):
        """Запуск интерактивной панели управления"""
        import time

        print("\n" + "=" * 50)
        print("KUBERNETES MONITORING DASHBOARD".center(50))
        print("=" * 50)

        while True:
            print("\n📊 МЕНЮ:")
            print("1. Проверить окружение")
            print("2. Развернуть приложение")
            print("3. Получить метрики Prometheus")
            print("4. Запустить Jenkins сборку")
            print("5. Проверить статус приложения")
            print("6. Создать недостающие файлы")
            print("7. Открыть Grafana")
            print("8. Выход")

            choice = input("\nВыберите действие (1-8): ").strip()

            if choice == '1':
                self.setup_environment()

            elif choice == '2':
                self.deploy_application()

            elif choice == '3':
                metrics = self.get_prometheus_metrics()
                if metrics:
                    print("\n📈 ТЕКУЩИЕ МЕТРИКИ:")
                    for key, value in metrics.items():
                        print(f"  {key}: {value}")

            elif choice == '4':
                self.run_jenkins_build()

            elif choice == '5':
                self.check_deployment_status()

            elif choice == '6':
                self.create_app_py()
                self.create_requirements()
                self.create_jenkins_script()

            elif choice == '7':
                self.open_grafana()

            elif choice == '8':
                print("👋 Выход из программы")
                break

            else:
                print("⚠️ Неверный выбор")

    def open_grafana(self):
        """Открытие Grafana"""
        try:
            print("🌐 Открытие Grafana...")

            # Получаем URL Grafana
            result = subprocess.run(
                ['minikube', 'service', '--url', '-n', 'monitoring', 'prometheus-grafana'],
                capture_output=True, text=True
            )

            if result.returncode == 0:
                url = result.stdout.strip()
                print(f"🔗 Grafana доступна по адресу: {url}")
                print("👤 Логин: admin")
                print("🔑 Пароль: prom-operator")

                # Пробуем открыть в браузере
                import webbrowser
                webbrowser.open(url)
            else:
                print("⚠️ Не удалось получить URL Grafana")
                print("Попробуйте: kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80")

        except Exception as e:
            print(f"❌ Ошибка: {e}")


def main():
    """Основная функция"""
    print("🚀 Запуск Kubernetes Monitoring Dashboard")
    print("Версия: 1.0")
    print("Автор: DevOps Project Integration")
    print("-" * 50)

    # Создаем монитор
    monitor = KubernetesMonitor()

    # Запускаем интерактивную панель
    monitor.dashboard()


if __name__ == "__main__":
    main()