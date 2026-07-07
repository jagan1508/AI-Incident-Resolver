from langchain_groq import ChatGroq
from langgraph.graph import START, END, StateGraph
from dotenv import load_dotenv
import psycopg2
from kubernetes import client, config


import os
from IPython.display import Image, display
from state import State
from langchain_core.prompts import ChatPromptTemplate
from prompts import classification_prompt,decision_prompt
from output import Category,Decision


load_dotenv()


from langgraph.graph import START, END, StateGraph

def classify(state: State)-> dict:
    model=ChatGroq(model="qwen/qwen3.6-27b",temperature=0)
    structured_model=model.with_structured_output(Category)
    chain = classification_prompt | structured_model
    result=chain.invoke({"event": state["raw_event"]})
    print(f"Classification result: {result.category}")  
    return {"classification": result.category}

def get_history(state: State) -> dict:
    print(state)
    fingerprint=state["fingerprint"]
    classification=state["classification"] ##to use this in select query to filter by classification as well
    with psycopg2.connect(host="localhost",database="incident_db", user="postgres" , password="password") as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, event_type, classification, decision, reasoning, actions_taken, outcome, created_at\
                            FROM incidents\
                            WHERE fingerprint = %s\
                            ORDER BY created_at DESC\
                            LIMIT 5;",(fingerprint,))##need to add another check with where for classification as i passed it for testing initially now
            rows=cursor.fetchall()
    if rows==[]:
        history_summary="No past incidents found for this fingerprint in the same category."
    else:
        lines=[]
        for i,row in enumerate(rows,1):
            line=(
            f"{i}. [{row[7]}] "
            f"event={row[1]}, "
            f"classification={row[2]}, "
            f"decision={row[3]}, "
            f"action={row[5]}, "
            f"outcome={row[6]}"
            )
        lines.append(line)
        history_summary=f"There are {len(rows)} past incidents found:\n"+"\n".join(lines)
        ##print(history_summary)
        
    
    return {"history": rows, "history_summary": history_summary}

def inspect(state: State) -> dict:
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    custom_api = client.CustomObjectsApi()
    deployment_found = False
    ret=apps_v1.list_namespaced_deployment(namespace="infrastructure-1")
    for i in ret.items:
        if i.metadata.name==state["resource_name"]:
            deployment_found = True
            replicas        = i.status.replicas or 0
            ready_replicas  = i.status.ready_replicas or 0
            available       = i.status.available_replicas or 0
            unavailable     = i.status.unavailable_replicas or 0
            strategy_type   = i.spec.strategy.type or "unknown"
            strategy_details = i.spec.strategy or {}
            container = i.spec.template.spec.containers[0]
            if container.resources.limits:
                cpu_limit    = container.resources.limits.get("cpu", "unknown")
                memory_limit = container.resources.limits.get("memory", "unknown")
            if container.resources.requests:
                cpu_request    = container.resources.requests.get("cpu", "unknown")
                memory_request = container.resources.requests.get("memory", "unknown")
            break
    if not deployment_found:
        return {
                "pod_status": "unknown",
                "restart_count": 0,
                "recent_k8s_events": [],
                "cluster_summary": f"Deployment '{state['resource_name']}' not found in namespace infrastructure-1."
            }
    try:
        pods = core_v1.list_namespaced_pod(
            namespace="infrastructure-1",
            label_selector=f"name={state['resource_name']}"
            )
            
        pod_statuses = []
        total_restarts = 0
        for pod in pods.items:
            phase = pod.status.phase or "unknown"
            pod_restart_count = 0
            container_statuses = pod.status.container_statuses
            if container_statuses:
                cs = container_statuses[0]
                pod_restart_count = cs.restart_count or 0
                total_restarts += pod_restart_count
            pod_statuses.append({
                    "name": pod.metadata.name,
                    "phase": phase,
                    "restarts": pod_restart_count,
                    "waiting_reason": cs.state.waiting.reason if cs.state.waiting else None})
        pod_status_summary = ", ".join([f"Pod Name:{p['name']}({p['phase']}, restarts={p['restarts']},waiting reason={p['waiting_reason']})" for p in pod_statuses])
        pod_status=pod_status_summary

    except Exception as e:
        pass
    cpu_usage = memory_usage = "unavailable"
    try:
        metrics = custom_api.list_namespaced_custom_object(
                group="metrics.k8s.io",
                version="v1beta1",
                namespace="infrastructure-1",
                plural="pods"
            )
        for item in metrics.get("items", []):
            if item["metadata"]["name"].startswith(state['resource_name']):
                containers = item.get("containers", [])
                if containers:
                    cpu_usage    = containers[0]["usage"].get("cpu", "unavailable")
                    memory_usage = containers[0]["usage"].get("memory", "unavailable")
                break
    except Exception:
        pass
    cluster_summary = f"""
            Deployment: {state['resource_name']} | Namespace: infrastructure-1
            Replicas: {ready_replicas}/{replicas} ready | Available: {available} | Unavailable: {unavailable}
            Strategy: {strategy_type} | Strategy details: {strategy_details})
            CPU  → Limit: {cpu_limit} | Request: {cpu_request} | Usage: {cpu_usage}
            Memory → Limit: {memory_limit} | Request: {memory_request} | Usage: {memory_usage}
            """.strip()
    #print(f"Cluster Summary:\n{cluster_summary}")
    #print(f"Pod Status Summary:\n{pod_status}")
    #print(f"Total Restarts: {total_restarts}")
    recent_events = []
    try:
        for pod in pod_statuses:
            events = core_v1.list_namespaced_event(
            namespace="infrastructure-1",
            field_selector=f"involvedObject.name={pod['name']}"  
        )
            for event in events.items:
                if event.type == "Warning":
                    recent_events.append({
                        "reason":    event.reason,
                        "message":   event.message,
                        "type":      event.type,
                        "count":     event.count or 1,
                        "timestamp": str(event.last_timestamp)
                    })
    except Exception as e:
        pass

    return {"pod_statuses": pod_statuses, "pod_status": pod_status, "restart_count": total_restarts, "recent_k8s_events": recent_events, "cluster_summary": cluster_summary}

def decide(state: State) -> dict:
    print("--------------------------")
    print(state['pod_statuses'])
    model=ChatGroq(model="llama-3.3-70b-versatile",temperature=0)
    structured_model=model.with_structured_output(Decision)
    chain = decision_prompt | structured_model
    result=chain.invoke({
        "event": state["raw_event"],
        "classification": state["classification"],
        "cluster_info": state["cluster_summary"],
        "history": state["history_summary"],
        "pod_status": state["pod_status"],
        "restart_count": state["restart_count"],
        "recent_k8s_events": state["recent_k8s_events"]
    })
    """print("--------------------------")
    print(f"Decision: {result.decision}")
    print(f"Reasoning: {result.reasoning}")
    print(f"Recommended Action: {result.recommended_action}")
    print(f"Confidence: {result.confidence}")"""
    return {
        "decision": result.decision,
        "reasoning": result.reasoning,
        "recommended_action": result.recommended_action,
        "confidence": result.confidence
    }

def escalate(state: State)-> dict:  
    print(f"Escalating incident {state['incident_id']} for human intervention.")
    
    return {"action_taken": "escalated", "outcome": "pending"}

def auto_remediate(state: State)-> dict:
    recommended_action = state["recommended_action"]
    print(f"Auto-remediating incident {state['incident_id']} with action: {recommended_action}")
    pod_statuses=state["pod_statuses"] or []
    config.load_kube_config()
    apps_v1 = client.AppsV1Api()
    core_v1 = client.CoreV1Api()
    if recommended_action == "restart_pod":
        unhealthy_pods = [
            p for p in pod_statuses
            if p["phase"] != "Running" or p["waiting_reason"] is not None
        ]
        if not unhealthy_pods:
            return {
                "action_taken": "no_action_self_healed",
                "outcome": "resolved"
            }
        actions=[]
        for pod in unhealthy_pods:
            pod_name = pod["name"]
            print(f"Restarting pod {pod_name}...")
            try:
                core_v1.delete_namespaced_pod(
                    name=pod_name,
                    namespace="infrastructure-1",
                    grace_period_seconds=0
                )
                action_taken = f"restarted {len(unhealthy_pods)} unhealthy pod(s): {[p['name'] for p in unhealthy_pods]}"
                print(f"Pod {pod_name} restarted successfully.")
            except Exception as e:
                print(f"Failed to restart pod {pod_name}: {e}")
                action_taken = f"failed to restart pod {pod_name}: {e}"
            actions.append(action_taken)
        return {
            "action_taken": ", ".join(actions),
            "outcome": "pending"
        }    
    elif recommended_action == "scale_up":
        print(f"Scaling up deployment {state['resource_name']}...")
        resource_name = state["resource_name"]
        try:
            replicas=apps_v1.read_namespaced_deployment_scale(name=resource_name, namespace="infrastructure-1").spec.replicas
            apps_v1.patch_namespaced_deployment_scale(name=resource_name, namespace="infrastructure-1", 
                                                    body={"spec": {"replicas": replicas + 1}})
            print(f"Deployment {resource_name} scaled up successfully.")
            action_taken = f"scaled up deployment {resource_name} from {replicas} to {replicas + 1} replicas"
        except Exception as e:
            print(f"Failed to scale up deployment {resource_name}: {e}")
            action_taken = f"failed to scale up deployment {resource_name}: {e}"
        return {"action_taken": action_taken, "outcome": "pending"}
    elif recommended_action == "rollback_deployment":
        print(f"Rolling back deployment {state['resource_name']}...")
        try:
            all_rn = apps_v1.list_namespaced_replica_set(namespace="infrastructure-1")
            selected_rn = [
                rn for rn in all_rn.items
                if rn.metadata.owner_references and any(ref.name == resource_name for ref in rn.metadata.owner_references)
            ]
            if len(selected_rn) < 2:
                print(f"No previous replica set found for deployment {state['resource_name']}. Rollback not possible.")
                return {"action_taken": f"rollback_not_possible: no previous replica set found:{state['resource_name']}", "outcome": "pending"}
            selected_rn.sort(
                    key=lambda rs: int(
                        rs.metadata.annotations.get(
                            "deployment.kubernetes.io/revision", "0"
                        )
                    )
                )
            previous_rs=selected_rn[-2]
            resource_name = state["resource_name"]
            previous_image = previous_rs.spec.template.spec.containers[0].image
            previous_revision = previous_rs.metadata.annotations.get(
                    "deployment.kubernetes.io/revision", "unknown"
                )
            print(f"Rolling back {resource_name} to revision {previous_revision} (image: {previous_image})")
            apps_v1.patch_namespaced_deployment(
                name=resource_name,
                namespace="infrastructure-1",
                body={
                    "spec": {
                        "template": {
                            "spec": {
                                "containers": [
                                    {"name": resource_name, "image": previous_image}
                                ]
                            }
                        }
                    }
                }
                )
            actions_taken = f"rollback:{resource_name}:to_revision_{previous_revision}:image_{previous_image}"
            print(f"Rollback successful — {resource_name} now running {previous_image}")
        except Exception as e:
            print(f"Failed to rollback deployment {resource_name}: {e}")
            actions_taken = f"failed_to_rollback:{resource_name}:error_{e}"
        return {"action_taken": actions_taken, "outcome": "pending"}
        
        
    else:
            print(f"Unexpected action '{recommended_action}' in auto_remediate — logging only")
            return {
                "action_taken": f"unexpected_action:{recommended_action}",
                "outcome": "pending"
            }

def log_outcome(state: State)-> dict:
    incident_id = state["incident_id"]
    classification = state["classification"]
    decision = state["decision"]
    reasoning = state["reasoning"]
    action_taken = state["action_taken"]
    outcome = state["outcome"]
    print(f"Logging outcome: {state['decision']} - {state['outcome']}")
    with psycopg2.connect(host="localhost",database="incident_db", user="postgres" , password="password") as conn:
            with conn.cursor() as cursor:
                cursor.execute("UPDATE incidents SET\
                                classification = %s,\
                                decision = %s,\
                                reasoning = %s,\
                                actions_taken = %s,\
                                outcome = %s\
                                WHERE id = %s",
                                (classification, decision, reasoning, action_taken, outcome, incident_id))
                conn.commit()
    print(f"Outcome logged for incident {incident_id}: decision={decision}, reasoning={reasoning}, action_taken={action_taken}, outcome={outcome}")
    return {} 

def route_decision(state: State)->str:
    return state["decision"]
    


builder=StateGraph(State)
builder.add_node("classify",classify)
builder.add_node("get_history",get_history)
builder.add_node("inspect_cluster",inspect)
builder.add_node("decide",decide)
builder.add_node("escalate",escalate)
builder.add_node("auto_remediate",auto_remediate)
builder.add_node("outcome",log_outcome)

builder.add_edge(START,"classify")
builder.add_edge("classify","get_history")
builder.add_edge("classify","inspect_cluster")

builder.add_edge("get_history","decide")
builder.add_edge("inspect_cluster","decide")
builder.add_conditional_edges("decide",route_decision,["escalate","auto_remediate","outcome"])
builder.add_edge("escalate","outcome")
builder.add_edge("auto_remediate","outcome")
builder.add_edge("outcome",END)

graph=builder.compile()

##For testing
initial_state = {
    "incident_id": 2,
    "fingerprint": "cpu_spike:payment-svc",
    "event_type": "cpu_spike",
    "resource_name": "payment-svc",
    "raw_event": {"type": "cpu_spike", "resource": "payment-svc", "fingerprint": "cpu_spike:payment-svc"},
    "created_at": "2026-06-30 12:00:00",
    "is_duplicate": False,
    "history": None,
    "history_summary": None,
    "classification": None,
    "decision": None,
    "reasoning": None,
    "pod_status": None,
    "restart_count": None,
    "recent_k8s_events": None,
    "cluster_summary": None,
    "action_taken": None,
    "outcome": None,
    "confidence": None,
    "recommended_action": None
}
"""initial_state = {
    "incident_id": 2,
    "fingerprint": "pod_crash:checkout-svc",
    "event_type": "pod_crash",
    "resource_name": "checkout-svc",
    "raw_event": {"type": "pod_crash", "resource": "checkout-svc", "fingerprint": "pod_crash:checkout-svc"},
    "created_at": "2026-06-30 12:00:00",
    "is_duplicate": False,
    "history": None,
    "history_summary": None,
    "classification": None,
    "decision": None,
    "reasoning": None,
    "pod_status": None,
    "restart_count": None,
    "recent_k8s_events": None,
    "cluster_summary": None,
    "action_taken": None,
    "outcome": None,
    "confidence": None,
    "recommended_action": None}"""
result =graph.invoke(initial_state)
#a=inspect(initial_state)

##Visualize the graph
'''png_data = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png_data)
print("Graph saved to graph.png")'''