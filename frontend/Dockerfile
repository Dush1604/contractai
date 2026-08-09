
# Stage 1: install dependencies and build the production bundle
FROM node:20-slim AS builder
WORKDIR /app

COPY package*.json ./
RUN npm ci

COPY . .

# NEXT_PUBLIC_ vars must be available at BUILD time, not just runtime —
# Next.js inlines them directly into the compiled client-side bundle.
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}

RUN npm run build

# Stage 2: lean runtime image — only what's needed to actually run the built app
FROM node:20-slim AS runner
WORKDIR /app

ENV NODE_ENV=production

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./package.json

RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 3000

CMD ["npm", "start"]
