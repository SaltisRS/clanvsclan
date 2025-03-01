FROM nginx:alpine

COPY ./nginx/default.conf /etc/nginx/conf.d/default.conf
WORKDIR /usr/share/nginx/html

COPY index.html .
COPY style.css .
COPY script.js .




