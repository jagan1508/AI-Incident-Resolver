from langchain_groq import ChatGroq
from langgraph.graph import START, END, StateGraph
from dotenv import load_dotenv
import os
from IPython.display import Image, display
from state import State

load_dotenv()

model=ChatGroq(model="openai/gpt-oss-20b")

from langgraph.graph import START, END, StateGraph

def classify(state: State)-> dict:
    return {"classification": "container_failure"}

def get_history(state: State) -> dict:
    return {"history": [], "history_summary": "No past incidents found."}

def inspect(state: State) -> dict:
   return {"pod_status": "CrashLoopBackOff", "restart_count": 3,"recent_k8s_events": [], "cluster_summary": "Pod is crash looping."}

def decide(state: State) -> dict:
    return {"decision": "escalate", "reasoning": "dummy reasoning", "confidence": "high", "recommended_action": "restart_pod"}

def escalate(state: State)-> dict:
    return {"action_taken": "escalated", "outcome": "pending"}

def auto_remediate(state: State)-> dict:
    return {"action_taken": "restart_pod", "outcome": "pending"}

def log_outcome(state: State)-> dict:
    print(f"Logging outcome: {state['decision']} - {state['outcome']}")
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


##Visualize the graph
'''png_data = graph.get_graph().draw_mermaid_png()
with open("graph.png", "wb") as f:
    f.write(png_data)
print("Graph saved to graph.png")'''