# syntax = docker/dockerfile:1

# Adjust NODE_VERSION as desired
ARG NODE_VERSION=22.13.1
FROM node:${NODE_VERSION}-slim AS base

LABEL fly_launch_runtime="Node.js"

# Node.js app lives here
WORKDIR /app

# Set production environment
ENV NODE_ENV="production"


# Throw-away build stage to reduce size of final image
FROM base AS build

# Install packages needed to build node modules
RUN apt-get update -qq && \
    apt-get install --no-install-recommends -y build-essential node-gyp pkg-config python-is-python3

# Install node modules
COPY package-lock.json package.json ./
RUN npm ci --include=dev

# Copy application code
COPY . .

# Accept build args for environment variables
ARG REACT_APP_API_BASE_URL
ARG REACT_APP_CLERK_PUBLISHABLE_KEY
ENV REACT_APP_API_BASE_URL=$REACT_APP_API_BASE_URL
ENV REACT_APP_CLERK_PUBLISHABLE_KEY=$REACT_APP_CLERK_PUBLISHABLE_KEY

# # Debug: Print environment variables (without exposing sensitive data)
# RUN echo "Environment variables set:" && \
#     echo "REACT_APP_API_URL: $REACT_APP_API_URL" && \
#     echo "REACT_APP_CLERK_PUBLISHABLE_KEY is set: $([ -n "$REACT_APP_CLERK_PUBLISHABLE_KEY" ] && echo 'YES' || echo 'NO')"

# Build application
RUN npm run build

# Remove development dependencies
RUN npm prune --omit=dev


# Final stage for app image
FROM base

# Copy built application
COPY --from=build /app /app

# Install serve to serve the production build
RUN npm install -g serve

# Start the server by default, this can be overwritten at runtime
EXPOSE 3000
CMD [ "serve", "-s", "build", "-l", "3000" ]
