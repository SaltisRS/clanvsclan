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
 

 # Use a Node.js runtime as the base image (for serving)
 FROM node:22.14.0-alpine
 

 # Set the working directory
 WORKDIR /app
 

 # Copy the built Nuxt.js application from the builder stage
 COPY --from=builder /app/.output/public ./public
 

 # Install serve (a simple static file server)
 RUN npm install -g serve
 

 # Expose port 80
 EXPOSE 80
 

 # Start the server on port 80
 CMD ["serve", "-s", "public", "-l", "80"]

