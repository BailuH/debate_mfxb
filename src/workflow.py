from langgraph.graph import StateGraph, START, END
from src.state import *
from src.agent import *

graph = StateGraph(CourtState)

judge = judge("A", "法官")
plaintiff = plaintiff("B", "原告律师")
defendant = defendant("C", "被告律师")

#增加节点
graph.add_node("debate_start", judge.debate_start)
graph.add_node("plaintiff_statement", plaintiff.plaintiff_statement)
graph.add_node("plaintiff_argue", plaintiff.plaintiff_argue)
graph.add_node("defendant_reply", defendant.defendant_reply)
graph.add_node("defendant_argue", defendant.defendant_argue)
graph.add_node("judge_summary", judge.judge_summary)
graph.add_node("judge_should_continue", lambda state:state)
graph.add_node("judge_verdict", judge.judge_verdict)
#增加边
graph.add_edge(START,"debate_start")
graph.add_edge("debate_start","plaintiff_statement")
graph.add_edge("plaintiff_statement","defendant_reply")
graph.add_edge("defendant_reply","judge_summary")
graph.add_edge("judge_summary","plaintiff_argue")
graph.add_edge("plaintiff_argue","defendant_argue")
graph.add_edge("defendant_argue","judge_should_continue")
graph.add_conditional_edges("judge_should_continue",judge.judge_should_continue,
                            {
                                "end" : "judge_verdict",
                                "continue" : "judge_summary"
                            })
graph.add_edge("judge_verdict", END)

app = graph.compile()

#可视化图（在脚本里输出png文件，因此不使用IPYTHON）
#with open("graph.png", "wb") as f:
    #f.write(app.get_graph().draw_mermaid_png())