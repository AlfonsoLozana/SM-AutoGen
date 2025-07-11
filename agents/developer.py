from typing import List
from models.interfaces import ApplicationDescription, NegotiationOffer
from pydantic import BaseModel
from autogen_core import (
    MessageContext,
    RoutedAgent,
    message_handler,
    type_subscription
)
from autogen_core.models import (
    AssistantMessage,
    ChatCompletionClient,
    LLMMessage,
)
from autogen_core import TopicId
from autogen_agentchat.agents import AssistantAgent
from autogen_core.model_context import BufferedChatCompletionContext

# Modelo unificado - eliminamos DeveloperNegotiationResponse
class DeveloperResponse(BaseModel):
    developer_estimated_time: str
    developer_budget_request: str
    conditions_accepted: bool
    reasoning: str

@type_subscription(topic_type="developer_topic")
class DeveloperAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient, min_budget: str, min_time: str):
        super().__init__("Developer")
        self._model_client = model_client
        self._history: List[LLMMessage] = []
        self._min_budget = min_budget
        self._min_time = min_time
        self._round = 0
        
        self._system_message = (
            "You are a DEVELOPER who wants to maximize your profit and time for a software project. "
            f"Your minimum acceptable budget is {min_budget} and minimum acceptable time is {min_time}. "
            "However, you should NOT reveal these minimums immediately. "
            "When estimating cost and time, always aim to request significantly more than your minimums to maximize profit. "
            "Start by requesting around 150-200% of your minimum budget and longer timeline than your minimum. "
            "Be professional but firm in your negotiation. "
            "Provide clear technical reasoning for your budget and time requests. "
            "If the client's offer is below your minimums, make a counter-offer explaining why you need more. "
            "You can gradually reduce your requests if the client pushes back, but never go below your minimums."
        )

    @message_handler
    async def handle_application_description(self, message: ApplicationDescription, ctx: MessageContext) -> None:
        """Handles the initial application description"""
        await self._process_negotiation(
            app_description=message.content,
            client_time=message.client_estimated_time,
            client_budget=message.client_budget_offer,
            iteration_number=1,
            is_initial=True,
            previous_dev_time=None,
            previous_dev_budget=None,
            client_reasoning=None
        )

    @message_handler
    async def handle_negotiation_offer(self, message: NegotiationOffer, ctx: MessageContext) -> None:
        """Handles negotiation offers from client"""
        await self._process_negotiation(
            app_description=message.application_description,
            client_time=message.client_estimated_time,
            client_budget=message.client_budget_offer,
            iteration_number=message.iteration_number + 1,
            is_initial=False,
            previous_dev_time=message.developer_estimated_time,
            previous_dev_budget=message.developer_budget_request,
            client_reasoning=message.reasoning
        )

    async def _process_negotiation(self, app_description: str, client_time: str, client_budget: str, 
                                 iteration_number: int, is_initial: bool, previous_dev_time: str = None, 
                                 previous_dev_budget: str = None, client_reasoning: str = None) -> None:
        """Unified method to process both initial and negotiation messages"""
        
        # Print status        print(f"{'='*60}")
        print(f"Developer: {'Received initial application' if is_initial else 'Received negotiation offer'}")
        print(f"Application: {app_description}")
        print(f"Client's time: {client_time}, budget: {client_budget}")
        if not is_initial:
            print(f"Previous dev offer - Time: {previous_dev_time}, Budget: {previous_dev_budget}")
        print(f"Developer limits - Min time: {self._min_time}, Min budget: {self._min_budget}")
        print(f"{'='*60}")
        

        prompt = self._generate_prompt(
            app_description, client_time, client_budget, is_initial, 
            previous_dev_time, previous_dev_budget, client_reasoning
        )
        

        result = await self._get_ai_response(prompt)
        

        negotiation_offer = self._create_negotiation_offer(
            app_description, client_time, client_budget, result, iteration_number
        )
        
        if not is_initial and result.conditions_accepted:
            print(f"{'!'*200}")
            print("¡ACUERDO ALCANZADO!")
            print(f"{'!'*200}")
            print(f"Aplicación: {app_description}")
            print(f"Tiempo acordado: {result.developer_estimated_time}")
            print(f"Presupuesto acordado: {result.developer_budget_request}")
            print(f"Razonamiento del desarrollador: {result.reasoning}")
            print(f"Oferta final del cliente - Tiempo: {client_time}, Presupuesto: {client_budget}")
            print(f"Iteración final: {iteration_number}")
            print(f"{'!'*200}")
            print("NEGOCIACIÓN TERMINADA - DESARROLLADOR ACEPTA CONDICIONES DEL CLIENTE")
            print(f"{'!'*200}")
            return  

        await self._finalize_response(result, negotiation_offer, is_initial)

    def _generate_prompt(self, app_description: str, client_time: str, client_budget: str, 
                        is_initial: bool, previous_dev_time: str = None, 
                        previous_dev_budget: str = None, client_reasoning: str = None) -> str:
        """Generate appropriate prompt based on context"""
        
        if is_initial:
            return (
                f"You have received a client request to develop the following application: {app_description}\n"
                f"The client estimates a timeline of {client_time} and offers a budget of {client_budget}.\n"
                f"Your minimum acceptable budget is {self._min_budget} and minimum acceptable time is {self._min_time}. "
                f"However, you want to maximize your profit and time, so propose significantly higher amounts. "
                f"Request around 150-200% of your minimum budget and a longer timeline than your minimum. "
                f"Provide professional technical reasoning for why you need more time and budget. "
                f"Do NOT reveal your minimum limits - keep them as your negotiation floor. "
                f"If the client's offer meets or exceeds your targets, you can accept it."
            )
        else:
            return (
                f"You are negotiating for this application: {app_description}\n"
                f"Your previous offer was: {previous_dev_time} timeline and {previous_dev_budget} budget.\n"
                f"The client has counter-offered: {client_time} timeline and {client_budget} budget.\n"
                f"Client's reasoning: {client_reasoning}\n"
                f"Your minimum acceptable budget is {self._min_budget} and minimum acceptable time is {self._min_time}. "
                f"Analyze the client's offer and decide if you should:\n"
                f"1. Accept it (if it meets or exceeds your minimums)\n"
                f"2. Make a counter-offer (reduce your previous offer but stay above minimums)\n"
                f"3. Reject it (if it's below your minimums)\n"
                f"Be strategic - you can reduce your offer from your previous one, but never go below your minimum limits."
            )

    async def _get_ai_response(self, prompt: str) -> DeveloperResponse:
        """Get AI response using the unified model"""
        agent = AssistantAgent(
            "assistant",
            model_client=self._model_client,
            system_message=self._system_message,
            output_content_type=DeveloperResponse,
            model_context=BufferedChatCompletionContext(buffer_size=5),
        )
        
        result = await agent.run(task=prompt)
        return get_last_developer_response(result.messages)

    def _create_negotiation_offer(self, app_description: str, client_time: str, 
                                client_budget: str, result: DeveloperResponse, 
                                iteration_number: int) -> NegotiationOffer:
        """Create NegotiationOffer object"""
        return NegotiationOffer(
            application_description=app_description,
            client_estimated_time=client_time,
            developer_estimated_time=result.developer_estimated_time,
            client_budget_offer=client_budget,
            developer_budget_request=result.developer_budget_request,
            iteration_number=iteration_number,
            conditions_accepted=result.conditions_accepted,
            sender="developer",
            reasoning=result.reasoning
        )

    async def _finalize_response(self, result: DeveloperResponse, 
                               negotiation_offer: NegotiationOffer, is_initial: bool) -> None:
        """Update history and send message"""
        history_message = (
            f"Developer's {'initial' if is_initial else 'counter-'}offer: "
            f"time {result.developer_estimated_time}, budget {result.developer_budget_request}. "
            f"Conditions accepted: {result.conditions_accepted}. Reasoning: {result.reasoning}"
        )
        
        self._history.append(AssistantMessage(content=history_message, source="developer"))
        print(f"Developer presents {'initial' if is_initial else 'counter-'}offer:\n{history_message}")
        
        self._round += 1
        
        await self.publish_message(
            negotiation_offer,
            topic_id=TopicId(type="client_topic", source=self.id.key)
        )

def get_last_developer_response(messages: List) -> DeveloperResponse:
    """Extract the last DeveloperResponse from the messages"""
    for msg in reversed(messages):
        if hasattr(msg, 'content') and isinstance(msg.content, DeveloperResponse):
            return msg.content
    return None
