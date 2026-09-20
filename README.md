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

## Versionen: Backend und Frontend getrennt

Jede Schicht hat ihre **eigene** Version im Image-Tag. Das UI zeigt beide
klar getrennt an:

| Chip | Quelle | Steuert |
|---|---|---|
| `API vX · Sommer/Winterreifen` | **Backend**-Image (`backend:v1/v2`) | Jahreszeit, Zähler, Goldfelge |
| `UI vX · Pod frontend-…` | **Frontend**-Image (`frontend:v1/v2`) | nur den statischen UI-Build |

> Wichtig: **Sommer/Winterreifen werden vom Backend gesteuert.** Die Anzeige
> kommt aus der API-Antwort (`/api/count`). Ein Frontend-Rollout ändert die
> Jahreszeit deshalb **nicht** – nur den `UI`-Chip (und Pod-Namen).

| Backend-Version | Bedeutung |
|---|---|
| `v1` | **Sommerreifen-Edition** |
| `v2` | **Winterreifen-Edition** |

Die Frontend-Version und der Pod-Name werden beim Container-Start aus
`APP_VERSION` und `POD_NAME` in `version.js` gerendert (nginx-Template).
Dadurch ist ein Frontend-Rollout sofort sichtbar: farbiger `UI`-Chip,
Ribbon oben, ein „UI aktualisiert“-Toast beim Versionswechsel und der
bedienende Pod. Die `FEATURE_GOLDEN_RIM` ConfigMap schaltet die
**Goldfelge** (Bonus-Reifen) ein – ein Beispiel für *Deploy ≠ Release*.

## Repository-Struktur

```
app/backend/            FastAPI-Anwendung + Dockerfile
app/frontend/           nginx + statisches UI + Dockerfile (version.js-Template)
k8s/                    Klassische Kubernetes-Manifeste (Teil 1 & 2)
argocd/                 ArgoCD AppProject + Application (Teil 2)
argo-rollouts/          Canary/Blue-Green + promote-all.sh (Teil 3)
loadtest/               Locust-Lasttest (optional auch als k8s-Job)
.github/workflows/      CI: baut Images und pusht sie nach GHCR
```

## Voraussetzungen

- Ein laufendes **k3s-Cluster** mit **ArgoCD** und **Argo Rollouts**.
  Wird mit dem Ansible-Playbook `ansible/playbook-k3s-cluster.yaml` aufgesetzt
  (k3s, ArgoCD, Argo Rollouts, metrics-server, Devtools).
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
- Rolling Update & Rollback des **Backends** (steuert die Jahreszeit):
  ```bash
  kubectl -n rudis-reifenklicker set image deployment/backend backend=ghcr.io/stafel/rudis-reifenklicker/backend:v2
  kubectl -n rudis-reifenklicker rollout status deployment/backend
  kubectl -n rudis-reifenklicker rollout undo deployment/backend
  ```
- Rolling Update des **Frontends** (UI-Chip wechselt, Jahreszeit bleibt!):
  ```bash
  kubectl -n rudis-reifenklicker set image deployment/frontend frontend=ghcr.io/stafel/rudis-reifenklicker/frontend:v2
  kubectl -n rudis-reifenklicker rollout status deployment/frontend
  # Reload im Browser: "UI v2" + ggf. Toast, Saison unverändert (Backend).
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

**Canary (Backend, gestufte Räderwechsel)**

```bash
kubectl argo rollouts -n rudis-reifenklicker get rollout backend -w
kubectl argo rollouts -n rudis-reifenklicker set image backend \
  backend=ghcr.io/stafel/rudis-reifenklicker/backend:v2   # Räderwechsel starten
kubectl argo rollouts -n rudis-reifenklicker promote backend   # nächste Stufe
kubectl argo rollouts -n rudis-reifenklicker abort backend     # Rollback
```

**Canary (Frontend, optional):** analog mit
`argo-rollouts/frontend-canary-rollout.yaml` und
`set image frontend frontend=...:v2`.

**Blue/Green (gesamte Umgebung auf einmal)**

Blue/Green schaltet die **komplette stateless Umgebung** (Frontend **und**
Backend) gemeinsam um. Beide Rollouts zeigen auf einen Preview-Service und
werden zusammen promoted:

```bash
kubectl -n rudis-reifenklicker apply -f argo-rollouts/analysis-template.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/backend-preview-service.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/frontend-preview-service.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/backend-bluegreen-rollout.yaml
kubectl -n rudis-reifenklicker apply -f argo-rollouts/frontend-bluegreen-rollout.yaml
# neue Versionen einspielen, dann die ganze Umgebung auf einmal umschalten:
./argo-rollouts/promote-all.sh
```

> Die **Datenbank** ist stateful und wird nicht mit umgeschaltet. Sie muss
> mit beiden Versionen kompatibel bleiben (vorwärts-kompatible Migrationen).


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
