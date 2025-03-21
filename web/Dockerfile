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
FROM unit:1.34.2-node22

# Copy the built Nuxt.js application from the builder stage
COPY --from=builder /app/.output/public /www/nuxt

# Define the Nginx Unit configuration
COPY unit.conf.json /tmp/unit.conf.json

RUN unitd --control unix:/run/control.unitd.sock < /tmp/unit.conf.json

# Expose port 80
EXPOSE 80

# Run Nginx Unit
CMD ["unitd", "--no-daemon"]
