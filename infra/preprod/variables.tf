variable "scw_access_key" {
  type      = string
  sensitive = true
}

variable "scw_secret_key" {
  type      = string
  sensitive = true
}

variable "scw_project_id" {
  type = string
}

variable "scw_region" {
  type    = string
  default = "fr-par"
}

variable "scw_zone" {
  type    = string
  default = "fr-par-1"
}

variable "domain_name" {
  type        = string
  description = "Zone DNS de base (ex: mondomaine.fr)"
}

variable "app_subdomain" {
  type        = string
  default     = "app"
  description = "Sous-domaine (ex: app → app.medokchat.fr)"
}

variable "ssh_public_key" {
  type        = string
  description = "Contenu de la clé SSH publique (~/.ssh/id_ed25519.pub)"
}

variable "allowed_ip" {
  type        = string
  description = "IP publique autorisée pour SSH (ex: 1.2.3.4/32)"
  default     = "0.0.0.0/0"
}
