IMAGE_REGISTRY ?= ghcr.io/stafel/rudis-reifenklicker
VERSION ?= v1
HOST ?= http://localhost:8080

.PHONY: help build up down logs loadtest validate reset

help:
	@echo "build     - Container-Images lokal bauen (Podman)"
	@echo "up        - Lokale Umgebung starten (podman compose)"
	@echo "down      - Lokale Umgebung stoppen"
	@echo "loadtest  - Locust-Lasttest gegen HOST (Default: $(HOST))"
	@echo "validate  - YAML-Manifeste linten"
	@echo "reset     - Rollout-Uebung zuruecksetzen (Deployments aus k8s/)"

build:
	podman build --build-arg APP_VERSION=$(VERSION) -t $(IMAGE_REGISTRY)/backend:$(VERSION) app/backend
	podman build --build-arg APP_VERSION=$(VERSION) -t $(IMAGE_REGISTRY)/frontend:$(VERSION) app/frontend

up:
	podman compose up --build -d

down:
	podman compose down -v

logs:
	podman compose logs -f

loadtest:
	cd loadtest && LOCUST_HOST=$(HOST) locust --config locust.conf

validate:
	yamllint k8s argocd argo-rollouts .github

reset:
	./argo-rollouts/rollout_reset.sh
