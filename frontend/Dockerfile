# =============================================================================
# PRODUCTION-READY FRONTEND DOCKERFILE
# =============================================================================
# Multi-stage build: development -> production
# Optimized for minimal image size and security

# =============================================================================
# STAGE 1: DEPENDENCIES
# =============================================================================
FROM node:20-alpine AS deps

WORKDIR /app

COPY package.json package-lock.json* ./

RUN npm ci

# =============================================================================
# STAGE 2: BUILD
# =============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG VITE_API_URL=/api
ARG VITE_WS_URL=ws://localhost:5000
ARG VITE_DEV_HOST=0.0.0.0

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_DEV_HOST=$VITE_DEV_HOST
ENV NODE_ENV=production

RUN npm run build

# =============================================================================
# STAGE 3: PRODUCTION SERVER (Nginx)
# =============================================================================
FROM nginx:alpine AS production

RUN rm /etc/nginx/conf.d/default.conf

COPY nginx.conf /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

RUN echo 'server_tokens off;' >> /etc/nginx/nginx.conf && \
    echo 'add_header X-Frame-Options "SAMEORIGIN" always;' >> /etc/nginx/conf.d/default.conf && \
    echo 'add_header X-Content-Type-Options "nosniff" always;' >> /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget --no-verbose --tries=1 --spider http://localhost:80/health || exit 1

CMD ["nginx", "-g", "daemon off;"]

# =============================================================================
# STAGE 4: DEVELOPMENT SERVER
# =============================================================================
FROM node:20-alpine AS development

WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY . .

ARG VITE_API_URL=http://localhost:5000
ARG VITE_WS_URL=http://localhost:5000
ARG VITE_DEV_HOST=0.0.0.0

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_WS_URL=$VITE_WS_URL
ENV VITE_DEV_HOST=$VITE_DEV_HOST
ENV NODE_ENV=development
ENV CHOKIDAR_USEPOLLING=true
ENV WATCHPACK_POLLING=true

EXPOSE 5173

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]