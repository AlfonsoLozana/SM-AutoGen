from typing import List
from models.interfaces import ApplicationDescription, InitialDescription, NegotiationOffer
from pydantic import BaseModel
from autogen_core import (
    RoutedAgent,
    message_handler,
    type_subscription,
    MessageContext
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
)
from autogen_core import TopicId

from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

    
class ClientResponse(BaseModel):
    time: str
    budget: str
    conditions_accepted: bool
    reasoning: str



@type_subscription(topic_type="client_topic")
class ClientAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, max_round: int, 
                 max_budget: str, max_time: str):
        super().__init__("Client")
        self._model_client = model_client
        self._history: List[LLMMessage] = []
        self._max_round = max_round
        self._max_budget = max_budget
        self._max_time = max_time
        self._round = 0
        
        self._system_message = (
            "You are a CLIENT who wants to hire a developer to build a software application. "
            f"Your maximum budget is {max_budget} and the maximum time you can wait is {max_time}. "
            "However, you should NOT reveal these limits immediately. "
            "Start by offering around 50-60% of your maximum budget and a shorter timeline than your maximum. "
            "You want to get the best deal possible, so negotiate strategically. "
            "Be professional but firm in your negotiations. "
            "You can gradually increase your offers if the developer pushes back, but never exceed your maximums. "
            "If the developer's counter-offer is within your limits, you can accept it."
        )

    @message_handler
    async def handle_application_description(self, message: InitialDescription, ctx: MessageContext) -> None:
        """Handles initial application description"""
        await self._process_negotiation(
            app_description=message.description,
            is_initial=True
        )

    @message_handler
    async def handle_negotiation_offer(self, message: NegotiationOffer, ctx: MessageContext) -> None:
        """Handles negotiation offers from developer"""
        
        if message.iteration_number > self._max_round:
            print(f"{'='*80}")
            print(f"MÁXIMO DE ITERACIONES ALCANZADO ({self._max_round})")
            print(f"ESTADO ACTUAL DE LA NEGOCIACIÓN - ITERACIÓN {message.iteration_number}")
            print(f"{'='*80}")
            print(f"Aplicación: {message.application_description}")
            print(f"Cliente - Tiempo: {message.client_estimated_time}, Presupuesto: {message.client_budget_offer}")
            print(f"Desarrollador - Tiempo: {message.developer_estimated_time}, Presupuesto: {message.developer_budget_request}")
            print(f"Condiciones aceptadas: {message.conditions_accepted}")
            print(f"Último remitente: {message.sender}")
            print(f"Razonamiento: {message.reasoning}")
            print(f"{'='*80}")
            print("NEGOCIACIÓN TERMINADA POR LÍMITE DE ITERACIONES")
            print(f"{'='*80}")
            return
    
        await self._process_negotiation(
            app_description=message.application_description,
            is_initial=False,
            negotiation_message=message
        )

    async def _process_negotiation(self, app_description: str, is_initial: bool, 
                                 negotiation_message: NegotiationOffer = None) -> None:
        """Unified method to process both initial and negotiation messages"""

        print(f"{'='*60}")
        if is_initial:
            print(f"Client: Starting negotiation for: {app_description}")
        else:
            print(f"Client: Received developer offer")
            print(f"Developer's time: {negotiation_message.developer_estimated_time}, budget: {negotiation_message.developer_budget_request}")
        print(f"Client limits - Max time: {self._max_time}, Max budget: {self._max_budget}")
        print(f"{'='*60}")
        
        prompt = self._generate_prompt(app_description, is_initial, negotiation_message)
        
        result = await self._get_ai_response(prompt)
        
        self._update_history(result, is_initial)
        
        if not is_initial and result.conditions_accepted:
            print(f"{'!'*200}")
            print("¡ACUERDO ALCANZADO!")
            print(f"{'='*80}")
            print(f"Aplicación: {app_description}")
            print(f"Tiempo acordado: {result.time}")
            print(f"Presupuesto acordado: {result.budget}")
            print(f"Razonamiento del cliente: {result.reasoning}")
            print(f"Iteración final: {negotiation_message.iteration_number + 1}")
            print(f"{'!'*200}")
            print("NEGOCIACIÓN TERMINADA - CONDICIONES ACEPTADAS")
            print(f"{'!'*200}")
            return  
        
        await self._send_message(app_description, result, is_initial, negotiation_message)

    def _generate_prompt(self, app_description: str, is_initial: bool, 
                        negotiation_message: NegotiationOffer = None) -> str:
        """Generate appropriate prompt based on context"""
        
        if is_initial:
            return (
                f"You want to hire a developer to build this application: {app_description}\n"
                f"Your maximum budget is {self._max_budget} and maximum timeline is {self._max_time}, "
                f"but you should start with a lower offer to negotiate a better deal. "
                f"Make an initial offer of around 50-60% of your maximum budget and a shorter timeline. "
                f"Explain what you want built and present your initial offer professionally. "
                f"Do NOT reveal your maximum limits - keep them as your negotiation ceiling."
            )
        else:
            return (
                f"You are negotiating for this application: {app_description}\n"
                f"Your previous offer was: {negotiation_message.client_estimated_time} timeline and {negotiation_message.client_budget_offer} budget.\n"
                f"The developer has counter-offered: {negotiation_message.developer_estimated_time} timeline and {negotiation_message.developer_budget_request} budget.\n"
                f"Developer's reasoning: {negotiation_message.reasoning}\n"
                f"Your maximum budget is {self._max_budget} and maximum timeline is {self._max_time}. "
                f"Analyze the developer's offer and decide if you should accept it, make a counter-offer, or reject it. "
                f"You can increase your offer from your previous one, but don't reveal your maximum limits."
            )

    async def _get_ai_response(self, prompt: str) -> ClientResponse:
        """Get AI response using the unified model"""
        agent = AssistantAgent(
            "assistant",
            model_client=self._model_client,
            system_message=self._system_message,
            output_content_type=ClientResponse,
            model_context=BufferedChatCompletionContext(buffer_size=5),
        )
        
        result = await agent.run(task=prompt)
        return get_last_client_response(result.messages)

    def _update_history(self, result: ClientResponse, is_initial: bool) -> None:
        """Update client history"""
        action = "initial proposal" if is_initial else "counter-offer"
        history_message = (
            f"My {action}: time {result.time}, budget {result.budget}. "
            f"Conditions accepted: {result.conditions_accepted}. "
            f"Reasoning: {result.reasoning}"
        )
        
        self._history.append(AssistantMessage(content=history_message, source="client"))
        print(f"Client presents {action}:\n{history_message}")
        self._round += 1

    async def _send_message(self, app_description: str, result: ClientResponse, 
                          is_initial: bool, negotiation_message: NegotiationOffer = None) -> None:
        """Send appropriate message based on context"""
        
        if is_initial:
            await self.publish_message(
                ApplicationDescription(
                    content=app_description,
                    client_estimated_time=result.time,
                    client_budget_offer=result.budget
                ),
                topic_id=TopicId(type="developer_topic", source=self.id.key)
            )
        else:
            await self.publish_message(
                NegotiationOffer(
                    application_description=app_description,
                    client_estimated_time=result.time,
                    developer_estimated_time=negotiation_message.developer_estimated_time,
                    client_budget_offer=str(result.budget),
                    developer_budget_request=negotiation_message.developer_budget_request,
                    iteration_number=negotiation_message.iteration_number + 1,
                    conditions_accepted=result.conditions_accepted,
                    sender="client",
                    reasoning=result.reasoning
                ),
                topic_id=TopicId(type="developer_topic", source=self.id.key)
            )


def get_last_client_response(messages: List) -> ClientResponse:
    """Extract the last ClientResponse from the messages"""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and isinstance(msg.content, ClientResponse):
            return msg.content
    return None
