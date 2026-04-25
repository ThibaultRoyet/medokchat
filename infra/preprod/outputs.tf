output "server_ip" {
  value       = scaleway_instance_ip.main.address
  description = "IP publique du VPS"
}

output "ssh_command" {
  value       = "ssh ubuntu@${scaleway_instance_ip.main.address}"
  description = "Commande SSH"
}

output "app_url" {
  value       = "https://${var.app_subdomain}.${var.domain_name}"
  description = "URL de l'application"
}
