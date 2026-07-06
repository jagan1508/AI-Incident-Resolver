from langchain_core.prompts import ChatPromptTemplate



classification_prompt= ChatPromptTemplate.from_messages([
("system",
 """You are an expert SRE incident classifier. Analyze the provided infrastructure event from a kubernetes cluster 
 and classify it accurately."""
),
("human",
""" First review the following kubernetes event properly.   
<event>
{event}
</event>"""
)
])

decision_prompt= ChatPromptTemplate.from_messages([
    ("system",
     """Your are an expert SRE decision engine for a kubernetes cluster.Your job is to decide whether to 
     auto-remediate, escalate to a human, or ignore an incident.
     
     Decision rules (follow these strictly):
        - auto_remediate: only if the fix is safe, known, and low-risk
        (e.g. restarting a crash-looping pod that has resolved before)
        - escalate: if uncertain, first occurrence, high risk, or no clear fix
        - ignore: if cluster is healthy and the alert appears to be a false positive
    Safety rules (never violate):
        - Never auto-remediate if restart_count < 1 (might be transient)
        - Never auto-remediate if all replicas are unavailable (too risky)
        - Always escalate on first occurrence (no history)
        - Always escalate if confidence is low
    Output format:
        Respond in JSON format with the following fields:
            {{"decision": "<auto_remediate|escalate|ignore>",
            "reasoning": "<plain English explanation, 2-3 sentences>",
            "recommended_action": "<restart_pod|scale_up|rollback_deployment|check_network|investigate|ignore>"}}
     """),
    ("human",
     """First review the following incident state properly.
        <event>
        {event}
        </event>
        Event classification:
        <classification>
        {classification}
        </classification>
        Information about the kubernetes cluster and the incident history is provided. Use this information to make a 
        decision on how to handle the incident.
        <kubernetes_cluster_info>
        {cluster_info}
        </kubernetes_cluster_info>
        <pod_status>
        {pod_status}
        </pod_status>
        <restart_count>
        {restart_count} 
        </restart_count>
        <recent_k8s_events>
        {recent_k8s_events}
        </recent_k8s_events>
        <incident_history>
        {history}
        </incident_history>
     """)
])