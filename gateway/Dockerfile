FROM nginx:alpine
RUN apk add --no-cache curl
COPY gateway/nginx.conf /etc/nginx/conf.d/default.conf
COPY gateway/html /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD curl -f http://localhost/health || exit 1
