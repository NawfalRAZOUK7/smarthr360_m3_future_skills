
# syntax=docker/dockerfile:1.4

# --- Builder stage: install ML deps, train models ---
FROM smarthr360-base:latest as builder

WORKDIR /app

# Copy ML code and requirements
COPY ml/requirements.txt ./ml/requirements.txt
COPY ml/ ./ml/

# Install ML requirements
RUN pip install --no-cache-dir -r ./ml/requirements.txt



FROM smarthr360-base:latest as builder
WORKDIR /app
# Ensure models directory exists in builder
RUN mkdir -p /app/ml/models
# ...existing code...

FROM smarthr360-base:latest as final
USER root

WORKDIR /app

# Copy only serving code and trained models from builder
COPY --from=builder /app/ml/ ./ml/
COPY --from=builder /app/ml/models/ ./ml/models/

# Copy entrypoint script from project root
COPY ./ml-entrypoint.sh /app/ml-entrypoint.sh
# Ensure dos2unix is installed and convert line endings
RUN apt-get update && apt-get install -y dos2unix && dos2unix /app/ml-entrypoint.sh
RUN chmod 755 /app/ml-entrypoint.sh
# Diagnostics: show permissions and file type

ENTRYPOINT ["sh", "/app/ml-entrypoint.sh"]
