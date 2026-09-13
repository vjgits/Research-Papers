from typing import Dict, List, Any, Optional
from pydantic import BaseModel, Field

class RetryConditions(BaseModel):
    null_retry: str = "Please continue."
    generic_retry: str = "Try again."
    verification_retry: str = "Check whether you missed anything; verify, escalate, or audit before answering."

class Checks(BaseModel):
    required_terms: List[str] = Field(default_factory=list)
    forbidden_terms: List[str] = Field(default_factory=list)
    numeric_expectations: List[Dict[str, Any]] = Field(default_factory=list)
    human_judged: bool = False

class Task(BaseModel):
    id: str
    mode: str
    task_family: str
    prompt: str
    expected_behavior: str
    retry_conditions: RetryConditions = Field(default_factory=RetryConditions)
    checks: Checks = Field(default_factory=Checks)
    metadata: Dict[str, Any] = Field(default_factory=dict)
