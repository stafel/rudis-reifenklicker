# syntax=docker/dockerfile:1
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY static/ /usr/share/nginx/html/

# Version und Pod-Name werden beim Container-Start aus den Umgebungs-
# variablen in version.js gerendert (nginx-Template-Mechanismus).
# APP_VERSION kommt aus dem Image-Build, POD_NAME aus der Downward API.
ARG APP_VERSION=v1
ENV APP_VERSION=${APP_VERSION} \
    NGINX_ENVSUBST_OUTPUT_DIR=/usr/share/nginx/html
LABEL org.opencontainers.image.version=${APP_VERSION}

COPY version.js.template /etc/nginx/templates/version.js.template

EXPOSE 80
