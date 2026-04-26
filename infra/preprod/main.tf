terraform {
  required_providers {
    scaleway = {
      source  = "scaleway/scaleway"
      version = "~> 2.49"
    }
  }
  required_version = ">= 1.5"

  backend "s3" {
    bucket                      = "medokchat-tf-state"
    key                         = "preprod/terraform.tfstate"
    region                      = "fr-par"
    endpoint                    = "https://s3.fr-par.scw.cloud"
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_region_validation      = true
    skip_metadata_api_check     = true
    force_path_style            = true
  }
}

provider "scaleway" {
  access_key = var.scw_access_key
  secret_key = var.scw_secret_key
  project_id = var.scw_project_id
  region     = var.scw_region
  zone       = var.scw_zone
}

# ── Clé SSH ───────────────────────────────────────────────────────────────────
resource "scaleway_iam_ssh_key" "main" {
  name       = "medokchat-preprod-key"
  public_key = var.ssh_public_key
}

# ── Groupe de sécurité (firewall) ─────────────────────────────────────────────
resource "scaleway_instance_security_group" "main" {
  name                    = "medokchat-preprod-sg"
  inbound_default_policy  = "drop"
  outbound_default_policy = "accept"

  inbound_rule {
    action   = "accept"
    protocol = "TCP"
    port     = 22
    ip_range = var.allowed_ip
  }

  inbound_rule {
    action   = "accept"
    protocol = "TCP"
    port     = 80
    ip_range = "0.0.0.0/0"
  }

  inbound_rule {
    action   = "accept"
    protocol = "TCP"
    port     = 443
    ip_range = "0.0.0.0/0"
  }
}

# ── IP publique ───────────────────────────────────────────────────────────────
resource "scaleway_instance_ip" "main" {}

# ── Instance VPS ──────────────────────────────────────────────────────────────
# DEV1-S : 2 vCPU, 2 GB RAM, 40 GB SSD — ~€4.27/mois
resource "scaleway_instance_server" "main" {
  name              = "medokchat-preprod"
  type              = "DEV1-S"
  image             = "ubuntu_jammy"
  ip_id             = scaleway_instance_ip.main.id
  security_group_id = scaleway_instance_security_group.main.id

  cloud_init = <<-EOF
    #cloud-config
    packages:
      - apt-transport-https
      - ca-certificates
      - curl
      - gnupg
    runcmd:
      - curl -fsSL https://get.docker.com | sh
      - usermod -aG docker ubuntu
      - apt-get install -y docker-compose-plugin
      - mkdir -p /opt/medokchat
      - chown ubuntu:ubuntu /opt/medokchat
  EOF
}

# ── DNS ───────────────────────────────────────────────────────────────────────
# Géré manuellement dans Scaleway Console (Domains & DNS → medokchat.fr)
# car le provider scaleway_domain_record v2.49 rejette le nom "app" (bug API)
