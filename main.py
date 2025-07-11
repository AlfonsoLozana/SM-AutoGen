from agents.developer import DeveloperAgent
from agents.client import ClientAgent
from models.interfaces import InitialDescription
from autogen_core import SingleThreadedAgentRuntime
from autogen_ext.models.ollama import OllamaChatCompletionClient
from autogen_core import TopicId
from config import load_config

async def run_requirements_gathering():
    # Cargar configuración
    config = load_config()
    
    # Configurar cliente del modelo
    model_client = OllamaChatCompletionClient(model=config.model)
    
    runtime = SingleThreadedAgentRuntime()
    
    # Registrar agentes con configuración
    await ClientAgent.register(runtime, "client", lambda: ClientAgent(
        model_client,
        max_round=5,
        max_budget=config.max_budget,
        max_time=config.max_time
    ))
    
    await DeveloperAgent.register(runtime, "developer", lambda: DeveloperAgent(
        model_client,
        min_budget=config.min_budget,
        min_time=config.min_time
    ))
    
    runtime.start()
    
    await runtime.publish_message(
        InitialDescription(description=config.description),
        topic_id=TopicId(type="client_topic", source="default")
    )
    
    await runtime.stop_when_idle()

def main():
    import asyncio
    asyncio.run(run_requirements_gathering())

if __name__ == "__main__":
    main()
