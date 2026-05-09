"""
EVIDRA — DAG Builder.

Translates the dynamic case context into a concrete execution plan.
Based on CANONICAL_01_Pipeline_DAG.
"""
from typing import Dict, Set

# Complete definition of all agents, tiers, and static dependencies
AGENT_REGISTRY = {
    # Tier 0
    "evidence_parser":      {"tier": 0, "depends_on": [], "required": True},
    
    # Tier 1
    "format_normalizer":    {"tier": 1, "depends_on": ["evidence_parser"], "required": True},
    
    # Tier 2 (Domain Agents)
    "autopsy_agent":        {"tier": 2, "depends_on": ["format_normalizer"], "required": False},
    "cdr_analyzer":         {"tier": 2, "depends_on": ["format_normalizer"], "required": False},
    "financial_analyzer":   {"tier": 2, "depends_on": ["format_normalizer"], "required": False},
    "device_extractor":     {"tier": 2, "depends_on": ["format_normalizer"], "required": False},
    "image_agent":          {"tier": 2, "depends_on": ["format_normalizer"], "required": False},
    
    # Tier 3 (ML Ensembles)
    "tod_agent":            {"tier": 3, "depends_on": ["autopsy_agent"], "required": False},
    "timeline_anomaly":     {"tier": 3, "depends_on": ["cdr_analyzer", "financial_analyzer", "device_extractor"], "required": False},
    "network_graph":        {"tier": 3, "depends_on": ["cdr_analyzer", "financial_analyzer"], "required": False},
    "collision_agent":      {"tier": 3, "depends_on": ["cdr_analyzer", "image_agent"], "required": False},
    
    # Tier 4 (Fusion Layer 1)
    "hotspot_engine":       {"tier": 4, "depends_on": ["timeline_anomaly", "collision_agent"], "required": True},
    "claim_extractor":      {"tier": 4, "depends_on": ["autopsy_agent", "cdr_analyzer", "financial_analyzer", "image_agent"], "required": True},
    
    # Tier 5 (NLI Mapping)
    "evidence_claim_mapper":{"tier": 5, "depends_on": ["claim_extractor", "hotspot_engine", "tod_agent", "network_graph"], "required": True},
    
    # Tier 6 (Bayesian & Bias)
    "hypothesis_manager":   {"tier": 6, "depends_on": ["evidence_claim_mapper"], "required": True},
    "bias_uncertainty":     {"tier": 6, "depends_on": ["hypothesis_manager"], "required": True},
    
    # Tier 7 (Next Best Evidence & Audit)
    "nbe_agent":            {"tier": 7, "depends_on": ["hypothesis_manager", "bias_uncertainty"], "required": True},
    "reasoning_replay":     {"tier": 7, "depends_on": ["nbe_agent"], "required": True},
}

def build_agent_plan(available_file_types: Set[str]) -> Dict[str, dict]:
    """
    Dynamically prune the DAG based on available evidence files.
    """
    plan = {}
    
    # 1. Start with always-required agents
    active_agents = set([k for k, v in AGENT_REGISTRY.items() if v["required"]])
    
    # 2. Add domain agents based on available files
    if "AUTOPSY_REPORT" in available_file_types:
        active_agents.add("autopsy_agent")
    if "CDR" in available_file_types:
        active_agents.add("cdr_analyzer")
    if "FINANCIAL_RECORDS" in available_file_types:
        active_agents.add("financial_analyzer")
    if "DEVICE_DATA" in available_file_types:
        active_agents.add("device_extractor")
    if "CCTV" in available_file_types or "IMAGE" in available_file_types:
        active_agents.add("image_agent")
        
    # 3. Propagate forward (if dependencies are met, activate ML/Fusion agents)
    changed = True
    while changed:
        changed = False
        for agent_id, config in AGENT_REGISTRY.items():
            if agent_id in active_agents:
                continue
            
            # An optional agent becomes active IF AT LEAST ONE of its optional dependencies is active
            # (unless it strictly requires all of them. Here, we assume partial data allows execution).
            # We filter out required upstream agents (Tier 0/1) to see if the specific domain triggers it.
            domain_deps = [d for d in config["depends_on"] if d in active_agents]
            
            # Special rule: timeline_anomaly requires at least one of its domain inputs
            if agent_id == "timeline_anomaly" and any(d in active_agents for d in ["cdr_analyzer", "financial_analyzer", "device_extractor"]):
                active_agents.add(agent_id)
                changed = True
            elif agent_id == "network_graph" and any(d in active_agents for d in ["cdr_analyzer", "financial_analyzer"]):
                active_agents.add(agent_id)
                changed = True
            elif agent_id == "tod_agent" and "autopsy_agent" in active_agents:
                active_agents.add(agent_id)
                changed = True
            elif agent_id == "collision_agent" and ("cdr_analyzer" in active_agents or "image_agent" in active_agents):
                active_agents.add(agent_id)
                changed = True

    # 4. Build final dict with pruned dependencies
    for agent_id in active_agents:
        orig = AGENT_REGISTRY[agent_id]
        # Keep only dependencies that are actually in the plan
        active_deps = [d for d in orig["depends_on"] if d in active_agents]
        plan[agent_id] = {
            "tier": orig["tier"],
            "depends_on": active_deps,
            "required": orig["required"]
        }
        
    return plan
