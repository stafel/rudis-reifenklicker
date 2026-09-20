/* Default-Konfiguration des Frontends.
 *
 * Im Cluster wird diese Datei durch die ConfigMap 'frontend-config'
 * ersetzt (siehe k8s/03-app-configmap.yaml). So kann das Frontend
 * konfiguriert werden, ohne das Image neu zu bauen.
 */
window.APP_CONFIG = {
  appName: "Rudis Reifenklicker",
  apiBase: "",
  pollMs: 2000
};
