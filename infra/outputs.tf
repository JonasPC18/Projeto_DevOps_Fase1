output "api_url" {
  description = "URL para acessar a API a partir do host Docker."
  value       = "http://127.0.0.1:${var.external_port}"
}

output "container_name" {
  description = "Nome do contêiner para consultar logs."
  value       = docker_container.app.name
}

output "volume_name" {
  description = "Volume persistente que contém o SQLite."
  value       = docker_volume.data.name
}
