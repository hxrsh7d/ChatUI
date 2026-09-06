# Multi-stage build: compile the Vite app, then serve the static output
# through nginx (which also proxies /api and /v1 to the backend container
# -- see nginx.conf).

FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# In the containerized deployment the frontend and backend are reached
# through the SAME origin (nginx proxies /api and /v1 -- see nginx.conf),
# so the default relative "/api" base (see src/services/api.ts) is
# correct as-is; no VITE_API_BASE override is needed for this build.
RUN npm run build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
