from pydantic import BaseModel
from typing import List

class Observation(BaseModel):
    description: str 
    evidence: str
    confidence: int

class Observations(BaseModel):
    observations: List[Observation]

class Insight(BaseModel):
    title: str
    insight: str
    context: str

class Insights(BaseModel):
    insights: List[Insight]

class FinalInsight(BaseModel):
    title: str
    tagline: str
    insight: str
    context: str
    merged: List[str]
    reasoning: str

class FinalInsights(BaseModel):
    insights: List[FinalInsight]
