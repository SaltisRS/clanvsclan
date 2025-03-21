
 FROM node:22.14.0-alpine

 WORKDIR /app

 COPY package*.json ./
 
 # Install dependencies
 RUN npm install
 
 COPY . .
 
 RUN npm run build

 EXPOSE 3000
 
 CMD ["node", ".output/server/index.mjs"]
