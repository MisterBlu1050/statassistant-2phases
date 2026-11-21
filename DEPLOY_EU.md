# Guide de Déploiement Production EU (Scaleway / OVH / Hetzner / Cloud Run Europe)

## 1. Option VPS Européen (Docker Compose + HTTPS automatique Caddy — 5 min)

```bash
# 1. Copier le projet sur un VPS EU (OVH Gravelines / Scaleway Paris / Hetzner Falkenstein)
cp .env.example .env
# Éditer .env : définir DOMAIN=stats.votre-domaine.eu, STAT_API_KEY et STAT_ADMIN_KEY
touch audit_log.jsonl

# 2. Démarrer avec certificat TLS Let's Encrypt automatique
docker compose up -d --build
```

Votre application bilingue NL/EN est en ligne en HTTPS avec en-têtes de sécurité (`HSTS`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`) et purge mémoire ZDR automatique (30 min).

## 2. Option Serverless (Google Cloud Run — région `europe-west1` Belgique)

```bash
gcloud run deploy stat-assistant \
  --source . \
  --region europe-west1 \
  --port 8000 \
  --set-env-vars "SESSION_TTL_MINUTES=30,STAT_ADMIN_KEY=votre-secret-admin" \
  --allow-unauthenticated
```

## 3. Administration & Suspension d'un utilisateur (Gouvernance XL AI)

```bash
# Suspendre immédiatement un compte
curl -X POST https://stats.votre-domaine.eu/api/admin/users/user-123/suspend \
  -H "X-Admin-Key: $STAT_ADMIN_KEY"

# Lever la suspension
curl -X DELETE https://stats.votre-domaine.eu/api/admin/users/user-123/suspend \
  -H "X-Admin-Key: $STAT_ADMIN_KEY"
```

## 4. Checklist Conformité XL AI avant ouverture clients
- [ ] `STAT_ADMIN_KEY` fort défini dans `.env` (jamais commité dans Git).
- [ ] Hébergement exclusivement en UE (`europe-west1` / Paris / Gravelines).
- [ ] Pour les clients RH/Clinique : palier **Local Expert (0 sortie réseau)** ou **API Enterprise ZDR** avec DPA signé.
- [ ] Vérifier régulièrement que `audit_log.jsonl` ne contient aucune donnée personnelle (uniquement empreintes SHA-256 et métadonnées d'actions).
