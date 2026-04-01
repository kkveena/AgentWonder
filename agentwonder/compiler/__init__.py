"""Compiler layer for AgentWonder.

Transforms YAML configuration into validated, resolved runtime plans.

Pipeline: YAML files -> raw dicts -> Pydantic models -> resolved references -> RuntimePlan
"""
