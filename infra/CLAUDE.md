# Infrastructure medokchat

## Vue d'ensemble

Stack : **Scaleway** (VPS DEV1-S + Container Registry + Object Storage) + **Caddy** (reverse proxy + TLS auto) + **Docker Compose**.

```
GitHub Actions
    │ push sur main (agents/) → build image → push registry → deploy SSH
    │ workflow_dispatch       → terraform apply / destroy
    ▼
Scaleway Container Registry
    │ image medokchat:latest
    ▼
VPS Scaleway DEV1-S (2 vCPU, 2 GB RAM, ~4€/mois)
    ├── Caddy :80/:443  → reverse proxy TLS automatique
    └── medokchat :7860 → interface Gradio
```

## Avant le premier déploiement

1. **Bucket S3 Terraform** — créer manuellement sur Scaleway Object Storage :
   - Nom : `medokchat-tf-state`
   - Région : `fr-par`

2. **Container Registry** — créer un namespace sur Scaleway Container Registry :
   - Ex : `rg.fr-par.scw.cloud/medokchat`

3. **Secrets & Variables GitHub** — configurer dans Settings → Secrets and variables → Actions (voir `.github/SECRETS.md`) :

   | Nom | Type | Valeur |
   |-----|------|--------|
   | `SCW_ACCESS_KEY` | Secret | Clé IAM Scaleway |
   | `SCW_SECRET_KEY` | Secret | Clé secrète IAM Scaleway |
   | `SSH_PRIVATE_KEY` | Secret | Contenu de `~/.ssh/id_ed25519` |
   | `SSH_PUBLIC_KEY` | Secret | Contenu de `~/.ssh/id_ed25519.pub` |
   | `ANTHROPIC_API_KEY` | Secret | Clé API Anthropic |
   | `REGISTRY` | Variable | `rg.fr-par.scw.cloud/medokchat` |
   | `VPS_HOST` | Variable | `app.medokchat.fr` |
   | `SCW_PROJECT_ID` | Variable | ID du projet Scaleway |
   | `DOMAIN_NAME` | Variable | `medokchat.fr` |
   | `APP_SUBDOMAIN` | Variable | `app` |
   | `LLM_MODEL_NAME` | Variable | `claude-sonnet-4-6` |

## Provisionner le VPS (première fois)

Déclencher le workflow **Terraform Apply** depuis GitHub Actions (onglet Actions → workflow_dispatch).

Il enchaîne automatiquement :
1. `terraform init` + `terraform apply` → crée VPS, firewall, IP, enregistrement DNS
2. Attend que Docker soit prêt sur le serveur (~2 min)
3. Attend la propagation DNS (~5 min max)
4. Copie le `.env` + `docker-compose.yml` + `Caddyfile` sur le VPS
5. Pull l'image et démarre les containers

## Déployer une nouvelle version

Push sur `main` avec des changements dans `agents/` → le workflow **Build & Deploy** se lance automatiquement.

Ou déclencher manuellement depuis l'onglet Actions.

## Détruire le VPS

Workflow **Terraform Destroy** (workflow_dispatch) — détruit le VPS, le firewall, l'IP et l'enregistrement DNS. Le bucket S3 du state et le Container Registry ne sont **pas** détruits.

## Fichiers

```
infra/
└── preprod/
    ├── main.tf            — VPS, firewall, IP, DNS (provider Scaleway)
    ├── variables.tf       — toutes les variables Terraform
    ├── outputs.tf         — IP, URL, commande SSH
    └── docker/
        ├── docker-compose.yml  — services Caddy + medokchat
        └── Caddyfile           — reverse proxy avec TLS auto

.github/
├── SECRETS.md             — liste complète des secrets à configurer
└── workflows/
    ├── deploy.yml          — build image + push + deploy sur push/main
    ├── terraform-apply.yml — provisionne + déploie (workflow_dispatch)
    └── terraform-destroy.yml — détruit l'infra (workflow_dispatch)

agents/
└── Dockerfile              — build multi-stage uv + Python 3.12-slim
```

## Variables d'environnement injectées sur le VPS

Régénérées à chaque déploiement depuis les secrets GitHub — rien de persistant sur le serveur.

| Variable | Source |
|----------|--------|
| `ANTHROPIC_API_KEY` | Secret GitHub |
| `LLM_MODEL_NAME` | Variable GitHub |
| `GRADIO_SERVER_NAME` | Hardcodé `0.0.0.0` (écoute toutes interfaces) |
| `GRADIO_SERVER_PORT` | Hardcodé `7860` |
| `REGISTRY` | Variable GitHub |
| `IMAGE_TAG` | Hardcodé `latest` |
| `DOMAIN` | Variable GitHub `DOMAIN_NAME` |

## Terraform state

Stocké dans le bucket S3 Scaleway `medokchat-tf-state` (région `fr-par`).  
Les credentials S3 utilisés par Terraform sont `SCW_ACCESS_KEY` / `SCW_SECRET_KEY` (passés via `AWS_ACCESS_KEY_ID` / `AWS_SECRET_ACCESS_KEY` dans la CI).
