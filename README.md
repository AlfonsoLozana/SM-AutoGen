# README.md - Sistema de Negociación Multiagente con AutoGen

```
# Sistema de Negociación Multiagente con AutoGen

## Pasos para Ejecutar el Programa

### 1. Instalar Ollama
Descarga e instala Ollama desde https://ollama.ai y descarga un modelo:
```

ollama pull mistral:latest

```

### 2. Instalar uv
Instala el gestor de paquetes uv:
```


# macOS/Linux

curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows

powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

```

### 3. Configurar el proyecto
Entra en el directorio del proyecto y edita `config.yaml` con tus parámetros:
```

model: "mistral:latest"
max_budget: "1500 eur"
max_time: "1 mes"
min_budget: "1200 eur"
min_time: "3 weeks"
description: "Tu descripción de aplicación aquí"

```

### 4. Instalar dependencias
```

uv sync

```

### 5. Ejecutar el programa
```

uv run main.py

```

¡Listo! El sistema iniciará la negociación entre el cliente y el desarrollador.
```

