# Rudis Reifenklicker

Eine kleine Drei-Schichten-Webanwendung zum **Lernen von Kubernetes und
Deployment-Strategien**. Statt Kekse zu klicken werden bei *Rudis Autoteile*
Reifen montiert.

Die App ist bewusst als klassische 3-Tier-Architektur aufgebaut:

```
                    Ingress (Traefik, k3s)
                      ├── /        ──▶ Service frontend ──▶ Deployment (stateless)
                      └── /api     ──▶ Service backend  ──▶ Deployment/Rollout (stateless)
                                                              │ postgres:5432
                                                              ▼
                                          Service postgres ──▶ StatefulSet + PVC (stateful)
```

- **Frontend** – statisches HTML/CSS/JS, ausgeliefert von nginx. Die montierte
  Reifen-Anzeige pollt die API.
- **Backend** – FastAPI (Python). Hält **keinen** eigenen Zustand, alle Daten
  liegen in PostgreSQL. Damit ist jeder Pod austauschbar (stateless).
- **Datenbank** – PostgreSQL als `StatefulSet` mit stabilem Namen (`postgres-0`),
  stabilem DNS und persistentem Volume (stateful).

## Versionen = Jahreszeiten

Die Backend-Version steckt im Image-Tag und wird im UI angezeigt:

| Version | Bedeutung |
|---|---|
| `v1` | **Sommerreifen-Edition** |
| `v2` | **Winterreifen-Edition** |

Dadurch wird bei einem Rolling-/Canary-/Blue-Green-Deployment sofort sichtbar,
welche Version eine Anfrage beantwortet hat. Die `FEATURE_GOLDEN_RIM`
ConfigMap schaltet die **Goldfelge** (Bonus-Reifen) ein – ein Beispiel für
*Deploy ≠ Release*.

## Repository-Struktur

```
app/backend/            FastAPI-Anwendung + Dockerfile
app/frontend/           nginx + statisches UI + Dockerfile
k8s/                    Klassische Kubernetes-Manifeste (Teil 1 & 2)
argocd/                 ArgoCD AppProject + Application (Teil 2)
argo-rollouts/          Canary- und Blue/Green-Rollouts (Teil 3)
loadtest/               Locust-Lasttest (optional auch als k8s-Job)
.github/workflows/      CI: baut Images und pusht sie nach GHCR
```

## Voraussetzungen

- Ein laufendes **k3s-Cluster** mit **ArgoCD** und **Argo Rollouts**.
  Wird mit dem Ansible-Playbook `ansible/playbook-k3s-cluster.yaml` aus dem
  DevOps-Repo aufgesetzt (k3s, ArgoCD, Argo Rollouts, metrics-server, Devtools).
- Zugriff auf die veröffentlichten Images unter
  `ghcr.io/stafel/rudis-reifenklicker/{backend,frontend}`.

## Lokale Entwicklung (ohne Cluster)

```bash
podman compose up --build      # oder: docker compose up --build
# Frontend:  http://localhost:8080
# API:       http://localhost:8000/api/count
podman compose down -v
```

## Images bauen

Die Images werden von GitHub Actions gebaut und nach GHCR gepusht:

- Bei einem Push auf `main` entstehen die Tags `main`, `dev`, `sha-*` und `latest`.
- Bei einem Git-Tag `v1` bzw. `v2` entstehen die Tags `v1` / `v2`
  (mit `APP_VERSION` fest im Image).
- Manuell über *Actions → build-push → Run workflow* (Eingabe z.B. `v2`).

Lokal:

```bash
make build VERSION=v1
```

## Teil 1 – Klassisches Kubernetes

```bash
kubectl apply -f k8s/
kubectl -n rudis-reifenklicker get pods,svc,pvc -w
```

**Experimente**

- `kubectl -n rudis-reifenklicker delete pod -l app=backend`
  → Zähler bleibt erhalten (der Zustand liegt in der DB).
- `kubectl -n rudis-reifenklicker delete pod postgres-0`
  → Daten bleiben erhalten (PVC wird neu gebunden).
- Drift: `kubectl -n rudis-reifenklicker scale deployment/backend --replicas=9`
  → ohne GitOps bleibt die Änderung bestehen (siehe Teil 2).
- Rolling Update & Rollback:
  ```bash
  kubectl -n rudis-reifenklicker set image deployment/backend backend=ghcr.io/stafel/rudis-reifenklicker/backend:v2
  kubectl -n rudis-reifenklicker rollout status deployment/backend
  kubectl -n rudis-reifenklicker rollout undo deployment/backend
  ```

Erreichbar ist die App über die Node-/VM-IP (Traefik-Ingress) oder per
Port-Forward:

```bash
kubectl -n rudis-reifenklicker port-forward svc/frontend 8080:80
```

## Teil 2 – GitOps mit ArgoCD

```bash
kubectl apply -f argocd/project.yaml
kubectl apply -f argocd/application.yaml
kubectl -n argocd port-forward svc/argocd-server 8080:443
```

ArgoCD synchronisiert den Ordner `k8s/` automatisch (`selfHeal` + `prune`).

**Drift-Experiment**

```bash
kubectl -n rudis-reifenklicker scale deployment/backend --replicas=9
# ArgoCD setzt den Wert aus Git selbstständig zurück.
```

## Teil 3 – Progressive Delivery mit Argo Rollouts

Der Controller wird vom Ansible-Playbook installiert. Für die Rollout-Übung
das klassische Deployment entfernen (gleicher Selektor!) und stattdessen das
Rollout anwenden. ArgoCD vorher auf manuellen Sync stellen, damit es den
Austausch nicht zurücksetzt:

```bash
argocd app set rudis-reifenklicker --sync-policy none   # oder Application löschen
kubectl -n rudis-reifenklicker delete deployment backend
kubectl -n rudis-reifenklicker apply -f argo-rollouts/backend-canary-rollout.yaml
```

**Canary**

```bash
kubectl argo rollouts -n rudis-reifenklicker get rollout backend -w
kubectl argo rollouts -n rudis-reifenklicker set image backend \
  backend=ghcr.io/stafel/rudis-reifenklicker/backend:v2   # Räderwechsel starten
kubectl argo rollouts -n rudis-reifenklicker promote backend   # nächste Stufe
kubectl argo rollouts -n rudis-reifenklicker abort backend     # Rollback
```

**Blue/Green**

```bash
kubectl -n rudis-reifenklicker apply -f argo-rollouts/backend-bluegreen-rollout.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/backend-preview-service.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/analysis-template.yaml
# neue Version einspielen und manuell freigeben:
kubectl argo rollouts -n rudis-reifenklicker promote backend
```

## Lasttest mit Locust

```bash
source ansible/.venv/bin/activate    # locust wurde vom Playbook installiert
make loadtest HOST=http://<VM-IP>
# oder direkt:
LOCUST_HOST=http://<VM-IP> locust -f loadtest/locustfile.py --headless -u 50 -r 5 -t 3m
```

Locust gibt am Ende die **Versionsverteilung** aus. Während eines Canary bei
`setWeight: 25` beantworten ca. 25 % der Klicks die Winterreifen-Version.
Der Lasttest hält auch die Fehlerrate bei einem Rolling Update sichtbar
(erwartet: 0 %).

## HPA (optional)

```bash
kubectl apply -f k8s/22-backend-hpa.yaml
# Last erzeugen und beobachten:
kubectl -n rudis-reifenklicker get hpa -w
kubectl top pods -n rudis-reifenklicker
```

## Plattform-Setup mit Ansible

Das Playbook liegt mit im Repo:

```bash
cd ansible
cp inventory.example inventory     # Hosts/User anpassen
ansible-playbook playbook-k3s-cluster.yaml
```

Das Playbook installiert k3s (Control + Agents), richtet kubectl und die
Devtools (helm, argocd, argo rollouts, k9s, podman, locust, ...) auf dem
Arbeitsplatz ein und installiert ArgoCD, Argo Rollouts sowie metrics-server.
Prometheus ist optional (`install_prometheus: true` in `group_vars/all.yml`).

## Hinweise für die Lehrperson

- Konzept-Zuordnung: stateless (`Deployment`) vs. stateful (`StatefulSet`),
  Service/Ingress, ConfigMap/Secret, PVC, Rolling/Canary/Blue-Green, GitOps & Drift.
- Das Passwort in `k8s/02-postgres-secret.yaml` ist ein **Platzhalter für die
  Übung** und darf nicht produktiv verwendet werden.
- Die GHCR-Packages müssen (einmalig) auf *public* gestellt werden, damit k3s
  die Images ohne `imagePullSecret` ziehen kann.
