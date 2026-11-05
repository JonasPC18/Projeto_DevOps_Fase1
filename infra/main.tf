resource "docker_network" "app" {
  name = "${var.project_name}-network"
}

resource "docker_volume" "data" {
  name = "${var.project_name}-data"
}

resource "docker_image" "app" {
  name         = "${var.project_name}:local"
  keep_locally = false

  build {
    context    = "${path.module}/.."
    dockerfile = "Dockerfile"
  }

  triggers = {
    source_hash = sha256(join("", [
      filesha256("${path.module}/../app.py"),
      filesha256("${path.module}/../Dockerfile")
    ]))
  }
}

resource "docker_container" "app" {
  name          = var.project_name
  image         = docker_image.app.image_id
  restart       = "unless-stopped"
  memory        = 128
  memory_swap   = 256 # Total de RAM + swap, alinhado ao padrão do Docker.
  cpus          = "0.5"
  read_only     = true
  security_opts = ["no-new-privileges:true"]
  wait          = true
  wait_timeout  = 60

  capabilities {
    drop = ["ALL"]
  }

  tmpfs = {
    "/tmp" = "rw,noexec,nosuid,size=16m"
  }

  ports {
    internal = 8000
    external = var.external_port
    ip       = "127.0.0.1"
  }

  volumes {
    volume_name    = docker_volume.data.name
    container_path = "/data"
  }

  networks_advanced {
    name = docker_network.app.name
  }

  log_opts = {
    "max-size" = "5m"
    "max-file" = "2"
  }
}
