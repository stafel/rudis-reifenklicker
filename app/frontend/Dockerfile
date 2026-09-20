# syntax=docker/dockerfile:1
FROM nginx:1.27-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY static/ /usr/share/nginx/html/

ARG APP_VERSION=v1
LABEL org.opencontainers.image.version=${APP_VERSION}

EXPOSE 80
