from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class UserNeed(BaseModel):
    need: str
    reasoning: str
    related_observations: List[int]
    level: Literal["high", "mid", "low"]
    need_type: Literal["explicit", "implicit"]

class UserNeedMerged(BaseModel):
    need: str
    confidence: int
    merged: List[str]
    reasoning: str
    step: int

class CombinedList(BaseModel):
    user_needs: List[UserNeedMerged]

class Insight(BaseModel):
    description: str 
    evidence: str
    generality: int

class InsightResponse(BaseModel):
    observations: List[Insight]

class Observation(BaseModel):
    description: str 
    evidence: str
    confidence: int
    interestingness: int

class ObservationResponse(BaseModel):
    observations: List[Observation]

class ObservationIDResponse(BaseModel):
    observations: List[int]

class NeedResponse(BaseModel):
    needs: List[UserNeed]

class NeedResponseMerged(BaseModel):
    no_needs_found: bool 
    user_needs: List[UserNeedMerged]

class Proposition(BaseModel):
    proposition: str
    reasoning: str
    confidence: int 
    decay: int 

class PropositionResponse(BaseModel):
    propositions: List[Proposition]

class Solution(BaseModel):
    solution: str
    description: str
    reasoning: str

class SolutionResponse(BaseModel):
    solutions: List[Solution]

class Cluster(BaseModel):
    members: List[int]
    evidence: str

class ClusterResponse(BaseModel):
    clusters: List[Cluster]

class Relation(BaseModel):
    source: int
    score: int
    target: List[int] 

class RelationsResponse(BaseModel):
    relations: Relation


class Task(BaseModel):
    task: str = Field(..., description="Name of the task")
    description: str = Field(..., description="1-2 sentence description of the task")
    importance: int = Field(..., ge=1, le=10, description="Importance rating from 1 to 10")


class NewGoalData(BaseModel):
    status: str
    goal: str
    description: str
    tasks: List[Task]
    context: List[str]

class ContinueGoalData(BaseModel):
    status: str
    goal: str
    description: str
    existing_tasks: List[Task]
    new_tasks: List[Task]
    context: List[str]

class Agent(BaseModel):
    name: str
    id: str
    purpose: str
    implementation: str
    feasibility: int

class AgentList(BaseModel):
    agents: List[Agent]

class Exists(BaseModel):
    exists: int
    utility: int

class Critique(BaseModel):
    code: str
    critique: str

class FilterResponse(BaseModel):
    score: int 
    reasoning: str

class ScenarioResponse(BaseModel):
    description: str


class Tool(BaseModel):
    name: str
    tool: str
    reasoning: str

class ToolResponse(BaseModel):
    tools: List[Tool]

class JudgeResponse(BaseModel):
    is_similar: int
    proposed_needs: List[str]

class ScoredNeedResponse(BaseModel):
    importance: int
    surprise: int
    reasoning: str

class IntrusionResponse(BaseModel):
    intruder: int
    reason: str

class CohesionResponse(BaseModel):
    confidence: int
    cohesion: int
    reasoning: str

class DuplicateResponse(BaseModel):
    judgement: int
    reason: str
    id: int

class GeneralJudge(BaseModel):
    judgement: int
    reason: str


### FOR PATTERN INDUCTION

class Reasoning(BaseModel):
    domain_knowledge: str
    workflows: List[str]
    class Config:
        allow_population_by_field_name = True


class Pattern(BaseModel):
    name: str
    description: str
    reasoning: Optional[Reasoning] = None
    input_type: str
    output_type: str
    user_behavior: Optional[str] = None
    ui_features: Optional[List[str]] = None
    design_guidelines: Optional[List[str]] = None

    class Config:
        allow_population_by_field_name = True


class PatternInductionResponse(BaseModel):
    patterns: List[Pattern]

    class Config:
        allow_population_by_field_name = True

class DatasetGenerationResponse(BaseModel):
    observations: List[str]

class NeedsJudgeResponse(BaseModel):
    is_similar: int
    similar_needs: List[int]
    reason: str


class Goal(BaseModel):
    goal: str
    description: str
    weight: int
    reasoning: str

class GoalResponse(BaseModel):
    goals: List[Goal]

class Reasoning(BaseModel):
    domain_knowledge: str
    workflows: List[str] 

class Pattern(BaseModel):
    name: str
    description: str
    reasoning: Reasoning | None = None
    input_type: str
    output_type: str
    user_behavior: str | None = None
    ui_features: List[str] | None = None
    design_guidelines: List[str] | None = None

class PatternInductionResponse(BaseModel):
    patterns: List[Pattern]
    reasoning: str

class PatternJudgeResponse(BaseModel):
    response: int
    reasoning: str

class Hypothesis(BaseModel):
    text: str
    description: str

class HypothesisResponse(BaseModel):
    hypotheses: List[Hypothesis]

class HypothesisEvalResponse(BaseModel):
    judgement: int
    reasoning: str
    support_observations: List[int]
    contradict_observations: List[int]

class Probability(BaseModel):
    id: str
    probability: int
    reasoning: str

class HypothesisRankResponse(BaseModel):
    likelihoods: List[Probability]