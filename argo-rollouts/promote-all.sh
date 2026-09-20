#!/usr/bin/env bash
# Schaltet die ganze (stateless) Umgebung auf einmal um:
# alle Argo-Rollouts der Anwendung werden nacheinander promoted.
#
#   ./argo-rollouts/promote-all.sh [NAMESPACE]
#
# Hinweis: Die Datenbank ist stateful und wird NICHT umgeschaltet. Sie
# muss mit beiden Versionen kompatibel bleiben (Schema-Migrationen
# vorwaerts-kompatibel gestalten).
set -euo pipefail

namespace="${1:-rudis-reifenklicker}"

rollouts="$(kubectl -n "${namespace}" get rollouts.argoproj.io -o name)"

if [ -z "${rollouts}" ]; then
  echo "Keine Rollouts im Namespace ${namespace} gefunden."
  exit 0
fi

for rollout in ${rollouts}; do
  echo ">> Promote ${rollout}"
  kubectl argo rollouts -n "${namespace}" promote "${rollout}"
done

echo "Alle Rollouts umgeschaltet."
