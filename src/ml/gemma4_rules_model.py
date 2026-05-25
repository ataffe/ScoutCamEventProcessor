import torch
from transformers import AutoProcessor, AutoModelForCausalLM
from PIL import Image
import logging
from pathlib import Path

from src.ml.rules_model import (
    RuleEvaluationResult, RuleEvaluationInput, RulesModel)
from src.ml.weights import download_weights_s3

logger = logging.getLogger("Guardian Cam Service Model")


class Gemma4RulesModel(RulesModel):
    def __init__(self, model_variant: str, model_weights_dir: str):
        self.model = None
        self.processor = None
        self.variant = model_variant
        self.weights_dir = model_weights_dir

    def init(self):
        model_path = self.weights_dir
        if (not Path(model_path).exists()
                or not any(Path(model_path).iterdir())):
            download_weights_s3('gemma4', self.variant, self.weights_dir)
            logger.info(f"Model downloaded to {model_path}")
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            dtype=torch.bfloat16,
            device_map="auto"
        )
        self.processor = AutoProcessor.from_pretrained(model_path)

        warm_up_message = [
            {"role": "system", "content": "You are a helpful assistant."}
        ]
        text = self.processor.apply_chat_template(
            warm_up_message,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        logger.info("Warming up model...")
        inputs = self.processor(
            text=text, return_tensors="pt").to(self.model.device)
        self.model.generate(**inputs, max_new_tokens=1024)
        logger.info("Warm up complete")

    def _build_rule_messages(
            self, rules: list[RuleEvaluationInput]) -> list[dict]:
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "system", "content": "Answer questions with yes or no"},
        ]
        for rule in rules:
            messages.append({
                "role": "user",
                "content": [
                    {"type": "image"},
                    {"type": "text", "text": f"is {rule.rule}?"},
                ],
            })
        return messages

    def evaluate_rules(
            self,
            rules: list[RuleEvaluationInput],
            image: Image.Image) -> list[RuleEvaluationResult]:
        rule_messages = self._build_rule_messages(rules)
        rule_text = self.processor.apply_chat_template(
            rule_messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False
        )
        inputs = self.processor(
            text=rule_text, images=image,
            return_tensors="pt").to(self.model.device)
        input_len = inputs["input_ids"].shape[-1]
        outputs = self.model.generate(**inputs, max_new_tokens=1024)
        response = self.processor.decode(
            outputs[0][input_len:], skip_special_tokens=False)
        response = self.processor.parse_response(response)['content'].lower()
        logger.debug(f'Response: {response}')
        return []
