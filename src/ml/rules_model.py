from abc import ABC, abstractmethod
from PIL import Image
from dataclasses import dataclass
from src.db.entities import Rule

@dataclass
class RuleEvaluationResult:
    rule_public_id: str
    rule_name: str
    is_triggered: bool

@dataclass
class RuleEvaluationInput:
    rule_public_id: str
    rule_name: str
    rule: str

    @classmethod
    def from_rule_entity(cls, rule_entity: Rule) -> "RuleEvaluationInput":
        return cls(
            rule_public_id=str(rule_entity.public_rule_id),
            rule_name=rule_entity.rule_nickname,
            rule=rule_entity.rule)

class RulesModel(ABC):
    @abstractmethod
    def init(self):
        pass

    @abstractmethod
    def evaluate_rules(self, rules: list[RuleEvaluationInput], image: Image.Image) -> list[RuleEvaluationResult]:
        pass
