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