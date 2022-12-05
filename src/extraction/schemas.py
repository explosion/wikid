""" Schemas for types used in this project. """

from typing import Set, Optional

from pydantic.fields import Field
from pydantic.main import BaseModel
from pydantic.types import StrictInt, StrictFloat


class Entity(BaseModel):
    """Schema for single entity."""

    qid: str = Field(..., title="Wiki QID")
    name: str = Field(..., title="Entity name")
    aliases: Set[str] = Field(..., title="All found aliases")
    count: StrictInt = Field(0, title="Count in Wiki corpus")
    description: Optional[str] = Field(None, title="Full description")
    article_title: Optional[str] = Field(None, title="Article title")
    article_text: Optional[str] = Field(None, title="Article text")


class Annotation(BaseModel):
    """Schema for single annotation."""

    entity_name: str = Field(..., title="Entity name")
    entity_id: Optional[str] = Field(None, title="Entity ID")
    start_pos: StrictInt = Field(..., title="Start character position")
    end_pos: StrictInt = Field(..., title="End character position")


class MentionEntity(BaseModel):
    """Schema for mention-entity pair."""

    mention: str = Field(..., title="Mention")
    entity_id: str = Field(..., title="Entity ID")
    rowid: StrictInt = Field(..., title="Row ID of entity in table `entities`")
    max_prior_prob: StrictFloat = Field(
        -1, title="Max. prior probability between entity and all matching aliases"
    )
    min_distance: StrictFloat = Field(
        -1, title="Min. distance between all aliases and this entity"
    )
    sum_occurence_count: StrictInt = Field(
        0, title="Summed up count of all aliases linked to this entity"
    )
