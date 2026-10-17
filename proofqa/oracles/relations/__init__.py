"""Metamorphic relation plugins and validation infrastructure."""

from __future__ import annotations

from proofqa.oracles.relations.base import Relation, WidgetClassifier
from proofqa.oracles.relations.false_relation import DeliberatelyFalseRelation
from proofqa.oracles.relations.filter import CategoryFilterRelation
from proofqa.oracles.relations.persistence import AddressPersistenceRelation
from proofqa.oracles.relations.runner import RelationRunner
from proofqa.oracles.relations.sort import SortRestorationRelation
from proofqa.oracles.relations.tape_oracle import MetamorphicOracle

__all__ = [
    "AddressPersistenceRelation",
    "CategoryFilterRelation",
    "DeliberatelyFalseRelation",
    "MetamorphicOracle",
    "Relation",
    "RelationRunner",
    "SortRestorationRelation",
    "WidgetClassifier",
]
