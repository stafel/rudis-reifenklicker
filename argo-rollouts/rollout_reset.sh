#!/usr/bin/env bash
# Setzt die Rollout-Uebung zurueck auf den Ausgangszustand (klassische
# Deployments aus k8s/).
#
# Hintergrund: Das strategy-Feld eines Argo-Rollout ist nicht mutierbar.
# Ein Wechsel Canary -> Blue/Green (gleicher Rollout-Name) erfordert
# Delete + Recreate.
#
#   ./argo-rollouts/rollout_reset.sh [NAMESPACE]
#
# Aequivalent von Hand:
#   kubectl -n rudis-reifenklicker delete rollout backend frontend
#   kubectl -n rudis-reifenklicker delete service backend-preview frontend-preview
#   kubectl -n rudis-reifenklicker apply -f k8s/20-backend-deployment.yaml
#   kubectl -n rudis-reifenklicker apply -f k8s/30-frontend-deployment.yaml
set -euo pipefail

namespace="${1:-rudis-reifenklicker}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ">> Rollouts und Preview-Services entfernen"
kubectl -n "${namespace}" delete rollout backend frontend --ignore-not-found
kubectl -n "${namespace}" delete service backend-preview frontend-preview --ignore-not-found

echo ">> Klassische Deployments wiederherstellen"
kubectl -n "${namespace}" apply -f "${script_dir}/../k8s/20-backend-deployment.yaml"
kubectl -n "${namespace}" apply -f "${script_dir}/../k8s/30-frontend-deployment.yaml"

echo "Rollout-Uebung zurueckgesetzt (Deployments aktiv)."
