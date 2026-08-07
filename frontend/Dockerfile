# syntax=docker/dockerfile:1
FROM node:20-alpine

WORKDIR /app

# Build-time configuration. Vite inlines VITE_* variables at build time, so they
# must be present before `npm run build` in a production image.
ARG VITE_API_BASE_URL=http://localhost:8000/api/v1
ARG VITE_WS_BASE_URL=ws://localhost:8000/ws
ARG VITE_GOOGLE_CLIENT_ID=
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_WS_BASE_URL=$VITE_WS_BASE_URL \
    VITE_GOOGLE_CLIENT_ID=$VITE_GOOGLE_CLIENT_ID \
    NODE_ENV=development

# Copy manifests first so `npm install` is cached across source changes.
COPY package.json ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev"]
