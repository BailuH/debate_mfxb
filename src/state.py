from typing import TypedDict,Union,Annotated
from langchain_core.messages import HumanMessage,ChatMessage
from langgraph.graph.message import add_messages

class evidence(TypedDict):
    speaker : str
    content : HumanMessage

class CourtState(TypedDict):
    case_info : str  #记录案件的基本信息
    case_evidence : Annotated[list[evidence], add_messages]  #记录当庭提出的所有证据
    phase : str
    messages : Annotated[list[Union[ChatMessage,HumanMessage]], add_messages]  #记录法庭辩论的内容
    speaker : str  #记录当前发言人
    human_role : str
    rounds : int
