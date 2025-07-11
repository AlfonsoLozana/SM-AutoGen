import yaml
from dataclasses import dataclass

@dataclass
class Config:
    model: str
    max_budget: str
    max_time: str
    min_budget: str
    min_time: str
    description: str

def load_config(config_file: str = "config.yaml") -> Config:
    """Carga la configuración desde el archivo YAML"""
    try:
        with open(config_file, 'r', encoding='utf-8') as file:
            data = yaml.safe_load(file)
            return Config(**data)
    except FileNotFoundError:
        print(f"Archivo {config_file} no encontrado. Usando configuración por defecto.")
        return Config(
            model="mistral:latest",
            max_budget="1500 eur",
            max_time="1 mes",
            min_budget="1200 eur",
            min_time="3 weeks",
            description="Aplicación software básica"
        )
