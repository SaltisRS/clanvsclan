FROM nginx:alpine

WORKDIR /usr/share/nginx/html

COPY index.html .
COPY style.css .
COPY script.js .

EXPOSE 3030

CMD ["nginx", "-g", "daemon off;"]
