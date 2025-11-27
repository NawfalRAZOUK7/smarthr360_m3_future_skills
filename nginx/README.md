# Nginx Configuration

This directory contains Nginx configuration files for the SmartHR360 Future Skills project.

## 📁 Files

- `nginx.conf` - Main Nginx configuration file for production deployment

## 🚀 Usage

### Development with Docker

The Nginx configuration is automatically used when running with Docker Compose:

```bash
docker-compose up
```

### Production Deployment

Copy the configuration to your Nginx installation:

```bash
# Copy to Nginx config directory
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf

# Test configuration
sudo nginx -t

# Reload Nginx
sudo nginx -s reload
```

## ⚙️ Configuration Details

### Upstream

- **django**: Proxies to Django application on port 8000

### Server Block

- **Port**: 80 (HTTP)
- **Server Name**: localhost
- **Client Max Body Size**: 100MB

### Location Blocks

#### `/` - Application Proxy

- Proxies all requests to Django application
- Sets proper headers for forwarding
- Timeout: 300s read, 75s connect

#### `/static/` - Static Files

- Serves collected static files from `/app/staticfiles/`
- Cache: 30 days
- Headers: Cache-Control "public, immutable"

#### `/media/` - Media Files

- Serves user-uploaded media from `/app/media/`
- Cache: 7 days
- Headers: Cache-Control "public"

### Security Headers

- `X-Frame-Options: SAMEORIGIN` - Prevents clickjacking
- `X-Content-Type-Options: nosniff` - Prevents MIME type sniffing
- `X-XSS-Protection: 1; mode=block` - XSS protection

## 🔧 Customization

### Change Port

Edit the `listen` directive:

```nginx
server {
    listen 8080;  # Change from 80 to 8080
    # ...
}
```

### Add SSL/HTTPS

Add SSL certificate configuration:

```nginx
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    # ...
}
```

### Adjust Timeouts

Modify proxy timeout settings:

```nginx
location / {
    proxy_read_timeout 600s;      # Increase to 10 minutes
    proxy_connect_timeout 120s;   # Increase to 2 minutes
    # ...
}
```

### Change Static/Media Paths

Update alias paths if your directory structure differs:

```nginx
location /static/ {
    alias /custom/path/to/staticfiles/;
    # ...
}
```

## 📊 Performance Tuning

### Worker Connections

Adjust based on expected traffic:

```nginx
events {
    worker_connections 2048;  # Increase from 1024
}
```

### Enable Gzip Compression

Add to http block:

```nginx
http {
    gzip on;
    gzip_types text/plain text/css application/json application/javascript;
    gzip_min_length 1000;
    # ...
}
```

### Add Rate Limiting

Protect against abuse:

```nginx
http {
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

    server {
        location /api/ {
            limit_req zone=api burst=20;
            # ...
        }
    }
}
```

## 🔍 Troubleshooting

### Check Configuration Syntax

```bash
nginx -t
```

### View Nginx Error Logs

```bash
# Docker
docker-compose logs nginx

# System Nginx
sudo tail -f /var/log/nginx/error.log
```

### Common Issues

**502 Bad Gateway**

- Check if Django application is running
- Verify upstream server address and port
- Check firewall rules

**Permission Denied on Static/Media**

- Ensure Nginx has read permissions
- Check SELinux/AppArmor settings
- Verify file ownership and permissions

**Upload Size Limit**

- Increase `client_max_body_size` directive
- Also check Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` setting

## 📚 References

- [Nginx Documentation](https://nginx.org/en/docs/)
- [Django Deployment with Nginx](https://docs.djangoproject.com/en/stable/howto/deployment/wsgi/uwsgi/)
- [Nginx Security Best Practices](https://nginx.org/en/docs/http/ngx_http_ssl_module.html)
