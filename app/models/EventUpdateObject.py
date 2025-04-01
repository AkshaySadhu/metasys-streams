from dataclasses import dataclass


@dataclass
class Item:
    presentValue: float
    id: str
    itemReference: str


@dataclass
class PresentValue:
    reliability: str
    priority: str


@dataclass
class Condition:
    presentValue: PresentValue


@dataclass
class EventUpdateObject:
    item: Item
    condition: Condition
