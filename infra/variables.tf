variable "docker_host" {
  description = "Socket do Docker Engine. Pode ser alterado para o Docker Desktop."
  type        = string
  default     = "unix:///var/run/docker.sock"
}

variable "project_name" {
  description = "Prefixo dos recursos exclusivos deste laboratório."
  type        = string
  default     = "devops-fase1-tarefas"

  validation {
    condition     = can(regex("^[a-z][a-z0-9-]{2,39}$", var.project_name))
    error_message = "Use 3 a 40 caracteres: letras minúsculas, números e hífen."
  }
}

variable "external_port" {
  description = "Porta local da API, sempre restrita a 127.0.0.1."
  type        = number
  default     = 8000

  validation {
    condition     = var.external_port >= 1024 && var.external_port <= 65535 && floor(var.external_port) == var.external_port
    error_message = "Use uma porta inteira entre 1024 e 65535."
  }
}
