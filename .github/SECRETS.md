# Secrets GitHub Actions requis

À configurer dans : **Settings → Secrets and variables → Actions**

## Infra Scaleway

| Nom | Type | Description |
|-----|------|-------------|
| `SCW_ACCESS_KEY` | Secret | Clé d'accès Scaleway (IAM) |
| `SCW_SECRET_KEY` | Secret | Clé secrète Scaleway (IAM) |
| `SSH_PRIVATE_KEY` | Secret | Clé privée SSH (`~/.ssh/id_ed25519`) |
| `SSH_PUBLIC_KEY` | Secret | Clé publique SSH (pour Terraform) |
| `REGISTRY` | Variable | Endpoint Container Registry (ex: `rg.fr-par.scw.cloud/medokchat`) |
| `VPS_HOST` | Variable | Hostname ou IP du VPS (ex: `medokchat.mondomaine.fr`) |
| `SCW_PROJECT_ID` | Variable | ID du projet Scaleway |
| `DOMAIN_NAME` | Variable | Zone DNS de base (ex: `mondomaine.fr`) |
| `APP_SUBDOMAIN` | Variable | Sous-domaine (ex: `medokchat`) |

## Application (runtime, injectés dans .env sur le VPS)

| Nom | Type | Description |
|-----|------|-------------|
| `ANTHROPIC_API_KEY` | Secret | Clé API Anthropic (`sk-ant-...`) |
| `LLM_MODEL_NAME` | Variable | Modèle Claude (ex: `claude-sonnet-4-6`) |

## Notes

- Le `.env` sur le VPS est régénéré à chaque déploiement depuis les secrets GitHub
- Créer le bucket S3 Scaleway `medokchat-tf-state` manuellement avant le premier `terraform apply`
- `terraform.tfvars` ne doit jamais être commité (déjà dans `.gitignore`)
