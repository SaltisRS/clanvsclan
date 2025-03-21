
FROM node:22.14.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY . .
RUN npm run build

EXPOSE 80
CMD ["node", ".output/server/index.mjs"]

