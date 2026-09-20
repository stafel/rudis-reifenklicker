# Rudis Reifenklicker

Drei-Schichten-Beispielanwendung für die Kubernetes-/Deployment-Übung
(`IN266 DevOps`). Statt Kekse zu klicken werden bei *Rudis Autoteile* Reifen
montiert.

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
3. **Progressive Delivery:** Canary und Blue/Green mit Argo Rollouts.
4. Optional: **Lasttest** (Locust) und **HPA**.

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

## Lokale Entwicklung (ohne Cluster)

```bash
podman compose up --build      # Frontend http://localhost:8080, API :8000
podman compose down -v
```

## Deployment

Images: `ghcr.io/stafel/rudis-reifenklicker/{backend,frontend}` (Tag `v1`/`v2`,
Jahreszeiten: v1 = Sommerreifen, v2 = Winterreifen – gesteuert vom **Backend**).
Die GHCR-Packages müssen einmalig auf *public* gestellt werden.

Cluster + Werkzeuge:

```bash
cd ansible
cp inventory.example inventory   # Hosts/User anpassen
ansible-playbook playbook-k3s-cluster.yaml --ask-become-pass
```

Rollout-Übung zurücksetzen (Strategiewechsel Canary ↔ Blue/Green):

```bash
make reset        # ruft argo-rollouts/rollout_reset.sh
```

## Lehrpersonen-Hinweise

- Passwort in `k8s/02-postgres-secret.yaml` ist ein **Übungs-Platzhalter**.
- `argocd/application.yaml` ist absichtlich **ohne** Self-Heal/Prune und ohne
  `ignoreDifferences` – das konfigurieren die Studierenden im Arbeitsblatt
  (inkl. HPA-Konflikt).
- Der HPA-Lasttest ist **vollständig optional**.
