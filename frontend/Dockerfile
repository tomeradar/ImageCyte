FROM node:22-slim

WORKDIR /app

# Copy dependency configs
COPY package*.json ./

# Install dependencies
RUN npm install

# Copy source code
COPY . .

# Expose dev port
EXPOSE 4200

# Start Angular local development server
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--port", "4200"]
