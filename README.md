# Rudis Reifenklicker

Drei-Schichten-Beispielanwendung für die Kubernetes-/Deployment-Übung.

- **Frontend** (stateless): statisches HTML/JS, nginx. `Deployment`.
- **Backend API** (stateless): FastAPI, hält keinen eigenen Zustand. `Deployment`.
- **Datenbank** (stateful): PostgreSQL als `StatefulSet` mit PVC.

```
Ingress ── / ──▶ frontend ──▶ Deployment
        └─ /api ─▶ backend  ──▶ Deployment ──▶ postgres (StatefulSet + PVC)
```

## Die Übung

Alle Aufgaben, Konfigurations- und Verständnisfragen stehen im **Arbeitsblatt**
(`Deployment Arbeitsblatt`, IN266). Kurzüberblick:

1. **Klassisches Kubernetes:** Manifeste aus `k8s/` mit `kubectl` ausrollen.
2. **GitOps mit ArgoCD:** Application konfigurieren, Drift erzeugen, Self-Heal.

## Repo-Struktur

```
app/backend/       FastAPI + Dockerfile
app/frontend/      nginx + statisches UI (version.js-Template) + Dockerfile
k8s/               klassische Kubernetes-Manifeste
argocd/            ArgoCD AppProject + Application
argo-rollouts/     Canary/Blue-Green + rollout_reset.sh
loadtest/          Locust-Lasttest (lokal)
ansible/           k3s + ArgoCD + Devtools Playbook
.github/workflows/ CI: Images nach GHCR
```
