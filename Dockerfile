FROM nginx:stable-alpine

LABEL org.opencontainers.image.title="site-staliszeduardo.com.br"
LABEL org.opencontainers.image.description="Site pessoal estatico de Eduardo Stalisz servido por Nginx"

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY index.html /usr/share/nginx/html/index.html
COPY styles.css /usr/share/nginx/html/styles.css
COPY script.js /usr/share/nginx/html/script.js
COPY static/ /usr/share/nginx/html/static/

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1

CMD ["nginx", "-g", "daemon off;"]
