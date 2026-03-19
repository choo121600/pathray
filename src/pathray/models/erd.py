"""ERD models for entity-relationship diagrams."""

from pydantic import BaseModel


class EntityField(BaseModel):
    """A field within an entity.

    Represents a column or attribute discovered from page structure.
    """

    name: str
    field_type: str
    nullable: bool = True
    is_primary: bool = False


class Entity(BaseModel):
    """An entity in the ERD.

    Represents a table or data object inferred from page forms/tables.
    """

    name: str
    fields: list[EntityField] = []
    source_url: str | None = None


class Relationship(BaseModel):
    """A relationship between two entities.

    Represents a foreign key or association inferred from page links/forms.
    """

    from_entity: str
    to_entity: str
    relation_type: str = "one-to-many"
    label: str | None = None
