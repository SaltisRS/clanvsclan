
FROM node:22.14.0-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --production

COPY . .
RUN npm run generate

EXPOSE 3000
CMD ["node", ".output/server/index.mjs"]

