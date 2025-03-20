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
 

 # Use a base image with Nginx Unit
 FROM nginx/unit:1.33.0-alpine
 

 # Copy the built Nuxt.js application from the builder stage
 COPY --from=builder /app/.output/public /www/nuxt
 

 # Define the Nginx Unit configuration
 RUN echo '{ \
  "listeners": { \
  "*:80": { \
  "pass": "routes" \
  } \
  }, \
  "routes": { \
  "share": { \
  "root": "/www/nuxt", \
  "index": "index.html" \
  } \
  } \
 }' > /tmp/config.json && \
  unitd --control unix:/run/control.unitd.sock < /tmp/config.json
 

 # Expose port 80
 EXPOSE 80
 

 # Run Nginx Unit
 CMD ["unitd", "--no-daemon"]
