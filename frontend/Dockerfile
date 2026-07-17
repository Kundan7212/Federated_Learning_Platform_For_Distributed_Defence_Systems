FROM node:20-alpine AS build

WORKDIR /app

COPY package*.json ./
RUN npm ci --silent

COPY . .
RUN npm run build

FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template

ENV BACKEND_HOST=backend
ENV BACKEND_PORT=8000
ENV NGINX_ENVSUBST_FILTER=^BACKEND_

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
