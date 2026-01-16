# DevOps-проект: Мониторинг ресурсов Kubernetes с Prometheus и Grafana

## Цель проекта
Настроить систему мониторинга кластера Kubernetes с использованием Prometheus и Grafana, а также отобразить метрики использования CPU, памяти (RAM) и диска.

---

## Этап 1. Развёртывание Prometheus и Grafana

Для начала был развёрнут кластер с помощью minikube, а затем установлены необходимые компоненты мониторинга:

```bash
minikube start
kubectl create namespace monitoring
helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring
```

*Скриншот состояния сервисов Prometheus (Endpoints):*
<img width="1848" height="335" alt="Service" src="https://github.com/user-attachments/assets/6c06de05-63ab-48d2-90bb-0f4b7de3b36a" />



---

## Этап 2. Проверка `deployment.yaml`

Далее был применён манифест `deployment.yaml`, который описывает деплой мониторинговых компонентов.

*Фрагмент кода deployment.yaml:*  
<img width="352" height="646" alt="Yaml_code" src="https://github.com/user-attachments/assets/fe640997-ee30-4cf8-a3dd-9a660d5be54c" />


---

## Запуск в Minikube

После деплоя приложения, проверяем состояние подов:

```bash
kubectl get pods -n monitoring
```
<img width="571" height="231" alt="Minik" src="https://github.com/user-attachments/assets/8002ba58-37cf-40e2-8576-a7169cdb8f14" />


---

## Этап 3. Метрики CPU

Метрика использует выражение:

```promql
100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[5m])) * 100)
```

*График загрузки CPU:*  
<img width="821" height="250" alt="CPU usage" src="https://github.com/user-attachments/assets/da50377a-def6-4085-97d0-1200587776fc" />


---

## Этап 4. Метрики памяти (Memory usage)

Метрика:

```promql
100 * (1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes))
```

*График использования памяти:*  
<img width="830" height="274" alt="Memory usage" src="https://github.com/user-attachments/assets/a285030a-5285-409e-85fe-f640db5da2db" />


---

## Этап 5. Метрики диска (Disk usage)

Для отслеживания дискового пространства используется:

```promql
100 - ((node_filesystem_avail_bytes{mountpoint="/"} * 100) / node_filesystem_size_bytes{mountpoint="/"})
```

*График использования диска:*  
<img width="832" height="262" alt="Disk usage" src="https://github.com/user-attachments/assets/5451de32-c2a2-4bbd-abbb-8b49eed02740" />


---

## Этап 6. Настройка алертов

В Grafana были настроены алерты на превышение порогов нагрузки — например, при загрузке CPU выше 80%.

*Пример созданного алерта:*  
<img width="1370" height="801" alt="Monitoring" src="https://github.com/user-attachments/assets/c03e6397-55d4-4f9a-a88e-3dad2738e721" />


---


## CI-процесс (jenkins-build.sh)
Скрипт, имитирующий сборку Docker-образа:
```bash
./jenkins-build.sh
```

## Результат
В результате была настроена система мониторинга, позволяющая:

- Отслеживать использование ресурсов кластера Kubernetes;
- Просматривать метрики CPU, RAM и диска в реальном времени;
- Настраивать уведомления (Alerts) о превышении порогов нагрузки.


---


