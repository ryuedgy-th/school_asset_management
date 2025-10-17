# Redis Setup Guide for Rate Limiting

## Overview

The `school_asset_management` module uses Redis for distributed rate limiting to protect signature endpoints from brute force attacks. Redis is required for production deployments with multiple workers but has a fallback mechanism for development environments.

## Why Redis?

**Problem with In-Memory Storage:**
- In-memory rate limiting (using Python dictionaries) only works in single-process mode
- In production (multi-worker with gunicorn/uwsgi), each worker has separate memory
- Attackers can bypass rate limits by hitting different workers

**Solution: Redis (Shared Storage):**
- Distributed rate limiting across all workers
- Atomic operations prevent race conditions
- Automatic key expiration (TTL) for cleanup
- Persistent across application restarts

## Installation

### Ubuntu/Debian

```bash
# Install Redis server
sudo apt update
sudo apt install redis-server

# Install Python Redis library
pip3 install redis

# Start Redis service
sudo systemctl start redis-server
sudo systemctl enable redis-server

# Verify installation
redis-cli ping
# Should respond: PONG
```

### Fedora/RHEL/CentOS

```bash
# Install Redis server
sudo dnf install redis

# Install Python Redis library
pip3 install redis

# Start Redis service
sudo systemctl start redis
sudo systemctl enable redis

# Verify installation
redis-cli ping
# Should respond: PONG
```

### Docker (Recommended for Production)

```bash
# Run Redis container
docker run -d \
  --name redis-odoo \
  -p 6379:6379 \
  --restart unless-stopped \
  redis:7-alpine

# Test connection
docker exec redis-odoo redis-cli ping
# Should respond: PONG
```

### Docker Compose (with Odoo)

```yaml
version: '3.8'

services:
  odoo:
    image: odoo:19
    depends_on:
      - db
      - redis
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - ./addons:/mnt/extra-addons
    ports:
      - "8069:8069"

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo-db:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

volumes:
  odoo-db:
  redis-data:
```

## Configuration

### Odoo Configuration Parameters

Configure Redis connection through Odoo's UI:

**Settings → Technical → Parameters → System Parameters**

| Parameter | Default | Description |
|-----------|---------|-------------|
| `school_asset.redis_host` | `localhost` | Redis server hostname |
| `school_asset.redis_port` | `6379` | Redis server port |
| `school_asset.redis_db` | `0` | Redis database number (0-15) |
| `school_asset.redis_password` | (empty) | Redis password (if authentication enabled) |
| `school_asset.rate_limit_requests` | `10` | Maximum requests per time window |
| `school_asset.rate_limit_window_seconds` | `3600` | Time window in seconds (1 hour) |

### Example Configuration

**Development (localhost):**
```
school_asset.redis_host = localhost
school_asset.redis_port = 6379
school_asset.redis_db = 0
school_asset.redis_password =
```

**Production (Docker):**
```
school_asset.redis_host = redis
school_asset.redis_port = 6379
school_asset.redis_db = 0
school_asset.redis_password = your_secure_password
```

**Production (External Server):**
```
school_asset.redis_host = redis.example.com
school_asset.redis_port = 6379
school_asset.redis_db = 1
school_asset.redis_password = your_secure_password
```

## Security Considerations

### Redis Password Authentication

For production, enable Redis authentication:

```bash
# Edit Redis config
sudo nano /etc/redis/redis.conf

# Add/uncomment:
requirepass YOUR_STRONG_PASSWORD

# Restart Redis
sudo systemctl restart redis-server
```

Update Odoo configuration:
```
school_asset.redis_password = YOUR_STRONG_PASSWORD
```

### Firewall Rules

If Redis is on a separate server:

```bash
# Only allow Odoo server to connect
sudo ufw allow from ODOO_SERVER_IP to any port 6379

# Deny all other connections
sudo ufw deny 6379
```

### Redis Configuration Hardening

```bash
# Edit /etc/redis/redis.conf

# Bind to specific interface (not 0.0.0.0)
bind 127.0.0.1

# Disable dangerous commands
rename-command FLUSHDB ""
rename-command FLUSHALL ""
rename-command CONFIG ""

# Set maximum memory
maxmemory 256mb
maxmemory-policy allkeys-lru

# Enable persistence (optional)
save 900 1
save 300 10
save 60 10000
```

## Fallback Mechanism

The module has a built-in fallback mechanism when Redis is unavailable:

### Fallback Behavior
- If Redis connection fails, the system logs a warning
- **Fail-open**: Requests are allowed to proceed (availability over security)
- Warning logged: "Rate limiting unavailable (Redis down). Allowing request from {ip}"
- Recommended: Set up Redis monitoring and alerts

### When Fallback is Used
1. Redis server is down
2. Redis library not installed
3. Network connectivity issues
4. Redis configuration errors

### Production Recommendation
**Do NOT rely on fallback in production!**
- Set up Redis monitoring (e.g., with Prometheus)
- Configure health checks
- Use Redis Sentinel or Cluster for high availability

## Monitoring

### Check Rate Limiting Status

```bash
# Check Redis keys
redis-cli keys "school_asset:rate_limit:*"

# View specific IP's attempts
redis-cli zrange "school_asset:rate_limit:192.168.1.100:signature" 0 -1 WITHSCORES

# Count current rate limit keys
redis-cli keys "school_asset:rate_limit:*" | wc -l
```

### Redis Stats

```bash
# Memory usage
redis-cli info memory

# Connection stats
redis-cli info clients

# Command stats
redis-cli info commandstats
```

### Odoo Logs

Check Odoo logs for rate limiting events:

```bash
# Development
tail -f odoo.log | grep "rate_limit"

# Production (systemd)
sudo journalctl -u odoo -f | grep "rate_limit"
```

**Example log entries:**
```
INFO Rate limit check passed for 192.168.1.100. Attempts: 3/10, Remaining: 7
WARNING Rate limit exceeded for IP 192.168.1.100 on signature endpoint. Attempts: 10/10
ERROR Failed to connect to Redis: Connection refused. Using fallback mode.
```

## Testing

### Test Redis Connection

```python
# Test from Python console
python3 << EOF
import redis
r = redis.Redis(host='localhost', port=6379, db=0)
print(r.ping())  # Should print: True
EOF
```

### Test Rate Limiting

```bash
# Install curl and jq
sudo apt install curl jq

# Test signature endpoint (adjust token)
for i in {1..15}; do
  echo "Request $i:"
  curl -s "http://localhost:8069/signature/checkout?token=YOUR_TOKEN" \
    | grep -o "Rate limit exceeded" || echo "Allowed"
  sleep 1
done
```

Expected output:
```
Request 1: Allowed
Request 2: Allowed
...
Request 10: Allowed
Request 11: Rate limit exceeded
Request 12: Rate limit exceeded
...
```

### Verify Multi-Worker Support

```bash
# Start Odoo with multiple workers
odoo-bin -d database -u school_asset_management --workers=4

# In another terminal, run concurrent requests
parallel -j 10 curl -s "http://localhost:8069/signature/checkout?token=TOKEN" ::: {1..20}

# Check Redis (should see rate limiting working across workers)
redis-cli keys "school_asset:rate_limit:*"
```

## Troubleshooting

### Issue: "Module redis not found"

**Solution:**
```bash
pip3 install redis
# or
pip3 install --user redis
```

### Issue: "Connection refused"

**Check if Redis is running:**
```bash
sudo systemctl status redis-server
# or
docker ps | grep redis
```

**Start Redis:**
```bash
sudo systemctl start redis-server
# or
docker start redis-odoo
```

### Issue: "Authentication required"

**Check Redis config:**
```bash
redis-cli CONFIG GET requirepass
```

**Update Odoo parameter:**
```
school_asset.redis_password = YOUR_PASSWORD
```

### Issue: Rate limiting not working in production

**Verify:**
1. Redis is accessible from all Odoo workers
2. All workers use the same Redis configuration
3. Network connectivity between Odoo and Redis
4. Check Odoo logs for Redis connection errors

```bash
# Test from Odoo server
redis-cli -h REDIS_HOST -p 6379 ping
```

## Performance Tuning

### Recommended Redis Settings

```bash
# /etc/redis/redis.conf

# Memory
maxmemory 512mb
maxmemory-policy allkeys-lru

# Network
tcp-backlog 511
timeout 0
tcp-keepalive 300

# Persistence (optional for rate limiting)
save ""  # Disable RDB snapshots
appendonly no  # Disable AOF

# Clients
maxclients 10000
```

### Odoo Configuration

```bash
# odoo.conf

# Enable multiple workers (production)
workers = 4
max_cron_threads = 2

# Database connection pool
db_maxconn = 64

# Timeouts
limit_time_cpu = 60
limit_time_real = 120
```

## High Availability Setup

For mission-critical deployments, use Redis Sentinel or Redis Cluster:

### Redis Sentinel (Master-Slave Replication)

```yaml
# docker-compose.yml
version: '3.8'

services:
  redis-master:
    image: redis:7-alpine
    command: redis-server --requirepass mypassword

  redis-slave:
    image: redis:7-alpine
    command: redis-server --slaveof redis-master 6379 --masterauth mypassword --requirepass mypassword

  redis-sentinel:
    image: redis:7-alpine
    command: redis-sentinel /etc/redis/sentinel.conf
    volumes:
      - ./sentinel.conf:/etc/redis/sentinel.conf
```

Update Odoo configuration to use Sentinel client.

## Summary

| Environment | Redis Required? | Fallback Safe? |
|-------------|----------------|----------------|
| Development (single worker) | No | Yes |
| Staging | Recommended | Yes |
| Production (multi-worker) | **YES** | **NO** |

**For production deployments:**
1. ✅ Install Redis server
2. ✅ Configure authentication
3. ✅ Set up monitoring
4. ✅ Test multi-worker scenarios
5. ✅ Document disaster recovery

---

**Last Updated:** 2025-10-17
**Module Version:** 19.0.1.6.0
**Redis Version Tested:** 7.x
