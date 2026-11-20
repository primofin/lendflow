# LendFlow web image. Build context: frontend/
# BACKEND_URL is read when the app is built (Next bakes the /api rewrite), so pass it as a build
# arg. On Fly it is the API's private address.
FROM node:22-alpine AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

FROM node:22-alpine AS build
WORKDIR /app
ARG BACKEND_URL=http://lendflow-api.internal:8000
ENV BACKEND_URL=$BACKEND_URL NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules node_modules
COPY . .
RUN npm run build

FROM node:22-alpine
WORKDIR /app
ARG BACKEND_URL=http://lendflow-api.internal:8000
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 HOSTNAME=0.0.0.0 PORT=3000 BACKEND_URL=$BACKEND_URL
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static .next/static
COPY --from=build /app/public public
USER node
EXPOSE 3000
CMD ["node", "server.js"]
