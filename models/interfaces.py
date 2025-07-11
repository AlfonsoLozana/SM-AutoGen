from dataclasses import dataclass
from typing import List

from dataclasses import dataclass

@dataclass
class InitialDescription:
    description: str

@dataclass
class ApplicationDescription:
    """Initial message from client describing the application"""
    content: str
    client_estimated_time: str
    client_budget_offer: str

@dataclass
class NegotiationOffer:
    """Unified message for both developer and client offers/counter-offers"""
    application_description: str
    client_estimated_time: str
    developer_estimated_time: str
    client_budget_offer: str
    developer_budget_request: str
    iteration_number: int
    conditions_accepted: bool
    sender: str  # "client" or "developer"
    reasoning: str

@dataclass
class FinalAgreement:
    """Final agreement message when both parties accept"""
    application_description: str
    agreed_time: str
    agreed_budget: str
    total_iterations: int
    agreement_reached: bool
