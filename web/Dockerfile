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
 

 # Use a Node.js runtime as the base image (for running the server)
 FROM node:22.14.0-alpine
 

 # Set the working directory
 WORKDIR /app
 

 # Copy the entire .output directory from the builder stage
 COPY --from=builder /app/.output ./.output
 

 # Expose port 3000
 EXPOSE 3000
 

 # Start the Nuxt.js server
 CMD ["node", "./.output/server/index.mjs"]
