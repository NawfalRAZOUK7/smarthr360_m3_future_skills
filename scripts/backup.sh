#!/bin/bash

# SmartHR360 Backup Script
# This script creates backups of the database and important files

set -e

# Configuration
BACKUP_DIR="/opt/smarthr360/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="smarthr360_backup_${TIMESTAMP}"

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

echo "Starting backup: $BACKUP_NAME"

# Database backup
echo "Creating database backup..."
docker-compose -f compose/docker-compose.prod.yml exec -T db pg_dump -U postgres smarthr360 > "$BACKUP_DIR/${BACKUP_NAME}_db.sql"

# Compress database backup
gzip "$BACKUP_DIR/${BACKUP_NAME}_db.sql"

# Backup media files
echo "Creating media files backup..."
tar -czf "$BACKUP_DIR/${BACKUP_NAME}_media.tar.gz" -C /opt/smarthr360 media/

# Backup ML artifacts
echo "Creating ML artifacts backup..."
tar -czf "$BACKUP_DIR/${BACKUP_NAME}_ml.tar.gz" -C /opt/smarthr360 artifacts/

# Backup configuration files
echo "Creating configuration backup..."
tar -czf "$BACKUP_DIR/${BACKUP_NAME}_config.tar.gz" \
    .env \
    compose/docker-compose.prod.yml \
    nginx/nginx.conf

# Create backup manifest
cat > "$BACKUP_DIR/${BACKUP_NAME}_manifest.txt" << EOF
Backup created: $(date)
Backup name: $BACKUP_NAME
Database: smarthr360
Files included:
- Database dump (compressed)
- Media files
- ML artifacts
- Configuration files

To restore:
1. Extract backup files
2. Restore database: psql -U postgres smarthr360 < ${BACKUP_NAME}_db.sql
3. Restore files to appropriate directories
EOF

# Clean up old backups (keep last 7 days)
echo "Cleaning up old backups..."
find "$BACKUP_DIR" -name "smarthr360_backup_*.tar.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "smarthr360_backup_*.sql.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "smarthr360_backup_*_manifest.txt" -mtime +7 -delete

echo "Backup completed successfully: $BACKUP_NAME"
echo "Backup location: $BACKUP_DIR"

# List current backups
echo "Current backups:"
ls -la "$BACKUP_DIR" | grep smarthr360_backup | head -10
