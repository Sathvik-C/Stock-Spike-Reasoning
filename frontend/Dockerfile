FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies
RUN npm ci

# Copy app
COPY frontend/src ./src
COPY frontend/public ./public
COPY frontend/vite.config.js .
COPY frontend/index.html .

# Build
RUN npm run build

# Expose port
EXPOSE 3000

# Serve
CMD ["npm", "run", "dev"]
