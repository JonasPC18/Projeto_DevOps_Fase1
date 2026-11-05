mock_provider "docker" {}

run "configuracao_do_laboratorio" {
  command = plan

  assert {
    condition     = docker_container.app.ports[0].ip == "127.0.0.1"
    error_message = "A API deve ficar acessível apenas no host local."
  }

  assert {
    condition     = docker_container.app.memory == 128 && docker_container.app.cpus == "0.5"
    error_message = "Os limites de recursos devem corresponder ao planejamento."
  }

  assert {
    condition     = docker_container.app.read_only && docker_container.app.wait
    error_message = "O contêiner deve usar raiz somente leitura e aguardar o healthcheck."
  }

  assert {
    condition     = output.api_url == "http://127.0.0.1:8000"
    error_message = "A URL precisa corresponder à porta configurada."
  }
}

run "rejeita_porta_privilegiada" {
  command = plan
  variables {
    external_port = 80
  }
  expect_failures = [var.external_port]
}

run "rejeita_porta_fracionaria" {
  command = plan
  variables {
    external_port = 8000.5
  }
  expect_failures = [var.external_port]
}

run "rejeita_nome_invalido" {
  command = plan
  variables {
    project_name = "Nome com espaços"
  }
  expect_failures = [var.project_name]
}
