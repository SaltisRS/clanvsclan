 # Use an official Node.js runtime as the base image
 FROM node:22.14.0-alpine AS builder
 

 # Set the working directory inside the container
 WORKDIR /app
 

 # Copy package.json and package-lock.json (if you have one)
 COPY package*.json ./
 

 # Install dependencies
 RUN npm install
 

 # Copy the rest of the application code
 COPY . .
 

 # Build the Nuxt.js application
 RUN npm run build
 

 # Use a lightweight web server to serve the static files
 FROM nginx:alpine
 

 # Copy the built Nuxt.js application from the builder stage
 COPY --from=builder /app/.output/public /usr/share/nginx/html
 

 # Expose port 80 for the web server
 EXPOSE 80
 

 # Start Nginx
 CMD ["nginx", "-g", "daemon off;"]
