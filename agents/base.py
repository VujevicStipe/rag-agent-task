from abc import ABC, abstractmethod
from core.context import AgentContext

class BaseAgent(ABC):
    
    @abstractmethod
    def run(self, context: AgentContext) -> AgentContext:
        pass
    
    def log_step(self, context: AgentContext, details: dict):
        from core.context import StepLog
        context.steps.append(StepLog(
            agent=self.__class__.__name__,
            details=details
        ))