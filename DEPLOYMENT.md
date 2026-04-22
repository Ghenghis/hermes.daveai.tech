# Deployment Guide - VPS (187.77.30.206)

This guide covers deploying the full Hermes ecosystem to the VPS.

## Prerequisites

- VPS access: `ssh root@YOUR_VPS_IP`
- Docker and Docker Compose installed on VPS
- Domain: `hermes.daveai.tech` pointing to VPS IP

## Step 1: Clone Repository on VPS

```bash
ssh root@YOUR_VPS_IP
cd /opt
git clone https://github.com/Ghenghis/hermes.daveai.tech.git
cd hermes.daveai.tech
```

## Step 2: Configure Environment

```bash
cp .env.example .env
nano .env
```

Fill in all required values:
- `SILICONFLOW_API_KEY`
- `MINIMAX_API_KEY`
- `DISCORD_TOKEN` (5 tokens for H1-H5)
- `DATABASE_URL`
- `VPS_IP=187.77.30.206`

## Step 3: Deploy with Docker Compose

```bash
docker-compose up -d
```

Verify all services running:
```bash
docker-compose ps
docker-compose logs -f
```

## Step 4: Deploy Hermes Discord Bots

```bash
cd hermes-full
docker-compose up -d hermes1 hermes2 hermes3 hermes4 hermes5
```

Bot channel assignments:
- hermes1 → #general
- hermes2 → #planning
- hermes3 → #design
- hermes4 → #issues
- hermes5 → #problems

## Step 5: Configure Nginx

```bash
cp deploy/nginx.conf /etc/nginx/sites-available/hermes.daveai.tech
ln -s /etc/nginx/sites-available/hermes.daveai.tech /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
```

## Step 6: SSL Certificate

```bash
certbot --nginx -d hermes.daveai.tech
```

## Step 7: Verify Deployment

```bash
# Check WebUI
curl http://localhost:3000

# Check API
curl http://localhost:8000/health

# Check Hermes bots
docker-compose logs hermes1 | tail -20
```

## Services & Ports

| Service | Port | URL |
|---------|------|-----|
| WebUI | 3000 | http://hermes.daveai.tech |
| API | 8000 | http://hermes.daveai.tech/api |
| PostgreSQL | 5432 | Internal only |
| Redis | 6379 | Internal only |
| Shiba Memory | 18789 | Internal only |

## Persistence & Restart Policy

All services use `restart: unless-stopped`.

**CRITICAL**: After VPS reboot, restore iptables rule for Shiba:
```bash
iptables -I INPUT -s 172.0.0.0/8 -p tcp --dport 18789 -j ACCEPT
```

To make persistent:
```bash
apt install iptables-persistent
netfilter-persistent save
```

## Troubleshooting

### Hermes bots not connecting to Shiba Memory
```bash
iptables -I INPUT -s 172.0.0.0/8 -p tcp --dport 18789 -j ACCEPT
```

### Database connection refused
```bash
docker-compose restart db
docker-compose logs db
```

### WebUI not loading
```bash
docker-compose logs webui
docker-compose restart webui
```
