from langchain_core.messages import SystemMessage, ChatMessage
from langgraph.types import interrupt,Command

from src.prompt import *
from src.state import *
from src.llmconfig import models


#大模型选择
ds_V3 = models["DeepSeek_V3"]
ds_R1 = models["DeepSeek_R1"]

class judge():

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role

    
    def debate_start(self, state: CourtState) -> CourtState:
        """法官宣布辩论开始,初始化CourtState，将话语权交给原告律师"""

        return {"phase" : "开庭阶段",
                "messages" : [ChatMessage(content=f"现在开始法庭辩论，请原告方进行陈述。\n案件信息：{state['case_info']}\n初步证据提交：{state['case_evidence']}",
                                           name = f"{self.name}({self.role})",
                                           role = "assistant")],
                "speaker" : "原告律师",
                "rounds" : 0
                }
    
    def judge_summary(self, state: CourtState) -> CourtState:
        """在这个节点，法官总结双方发言，进一步归纳出争议焦点，引导双方就焦点问题展开进一轮的辩论"""

        if state["speaker"] != "法官":
            return state
    
        if state["human_role"] == "法官":
            user_input = interrupt("现在请你仔细阅读双方的发言，归纳双方的争议焦点，引导双方就焦点进行辩论")
            return {
                "messages" : [HumanMessage(content=user_input, name = f"{self.name}({self.role})")],
                "speaker" : "原告律师",
                "phase" : "交叉质证"
            }
        else:
            model_input = [SystemMessage(content=SUMMARY)] + state["messages"]
            response = ds_R1.invoke(model_input)
            return {
                "messages" : [ChatMessage(content=response.content, name = f"{self.name}({self.role})",role = "assistant")], 
                "speaker" : "原告律师",
                "phase" : "交叉质证"
            }
    
    def judge_should_continue(self, state: CourtState) -> str:
        """这是一个关键的路由节点，在这个节点由法官决定是否要进行新一轮的辩论，判断逻辑是根据辩论轮次（显式规定），和LLM自行
        根据上下文进行判断是否进行新一轮辩论"""

        state["rounds"] +=1  #计算当前辩论场次
        if state["rounds"] >= 3:
            return "end"
        
        messages = state.get("messages", [])  #面向对象的代码风格
        # 格式化消息
        content = "\n".join(
            [f"{msg.name.upper()}: {msg.content}" for msg in messages]
        )

        model_input = judge_prompt.format(messages = content)
        response = ds_R1.invoke(model_input)

        decision = response.content.strip().lower()
        if decision not in ["continue", "end"]:
            decision = "continue" #兜底处理

        return decision
    
    def judge_verdict(self, state: CourtState) -> CourtState:
        """在这个节点，法官先前已经认为双方辩论已经足够充分，因此法官对本案件进行总结，并进行裁决"""
        
        if state["speaker"] != "法官":
            return state
        
        if state["human_role"] == "法官":
            user_input = interrupt("既然双方辩论已经充分，请你宣布审判结果")
            return {
                "messages" : [HumanMessage(content = user_input, name = f"{self.name}({self.role})")],
                "phase" : "休庭小结"
            }
        else:
            model_input = [SystemMessage(content = VERDICT)] + state["messages"]
            response = ds_R1.invoke(model_input)
            return{
                "messages" : ChatMessage(content = response.content, role = f"{self.name}({self.role})"),
                "phase" : "休庭小结"
            }
        

class plaintiff():

    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role


    def plaintiff_statement(self, state: CourtState) -> CourtState:
        """在这个节点，原告做出开场指控陈述，法庭状态记录原告发言，并将话语权交给被告律师"""

        #多重检查
        if state["speaker"] != "原告律师":
            return state
        
        if state["human_role"] == "原告律师":
            # 等待人类原告输入
            user_input = interrupt("现在是开庭阶段，请你作出有力的开庭指控陈述吧！")
            return {"messages" : [HumanMessage(content=user_input, name = f"{self.name}({self.role})")],
                    "speaker" : "被告律师"
                    }
        else:
            # AI原告生成陈述
            model_input = [SystemMessage(content=STATEMENT_PROMPT)] + state["messages"]
            response = ds_V3.invoke(model_input)
            return {"messages" : [ChatMessage(content=response.content, name = f"{self.name}({self.role})", role = "assistant")],
                    "speaker" : "被告律师"
                    }
    
    def plaintiff_argue(self, state: CourtState) -> CourtState:
        """在这个节点，原告承接法官的引导，就被告提出的质疑做出回应，进行新一轮辩论法庭状态记录原告发言，并将话语权交给被告律师"""

        #多重检查
        if state["speaker"] != "原告律师":
            return state
        
        if state["human_role"] == "原告律师":
            # 等待人类原告输入
            user_input = interrupt("请你根据法官总结的焦点争议，针对被告的反驳作出回应，并进一步论述自己的主张！")
            return {"messages" : [HumanMessage(content=user_input, name = f"{self.name}({self.role})")],
                    "speaker" : "被告律师"
                    }
        else:
            # AI原告生成陈述
            model_input = [SystemMessage(content=ARGUE_PROMPT_PL)] + state["messages"]
            response = ds_V3.invoke(model_input)
            return {"messages" : [ChatMessage(content=response.content, name = f"{self.name}({self.role})", role = "assistant")],
                    "speaker" : "被告律师"
                    }
        

class defendant():
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role


    def defendant_reply(self, state: CourtState) -> CourtState:
        """在这个节点，被告针对原告的指控陈述做出答辩，法庭状态记录被告发言，并将话语权移交给法官
        由法官主持进行进一步的交叉质证辩论环节"""


        if state["speaker"] != "被告律师":
            return state
        
        if state["human_role"] == "被告律师":
            user_input = interrupt("现在请你就原告做出的开场陈述，进行有力的抗辩吧！")

            return {"messages" : [HumanMessage(content=user_input, name = f"{self.name}({self.role})")],
                    "speaker" : "法官"
                    }
        else:
            model_input = [SystemMessage(content=DEMURRER_PROMPT)] + state["messages"]
            response = ds_V3.invoke(model_input)
            return {"messages" : [ChatMessage(content=response.content, name = f"{self.name}({self.role})", role = "assistant")],
                    "speaker" : "法官"
                    }
        
    def defendant_argue(self, state: CourtState) -> CourtState:
        """在这个节点，被告针对原告的指控陈述做出答辩，法庭状态记录被告发言，并将话语权移交给法官
        由法官进一步组织发言"""


        if state["speaker"] != "被告律师":
            return state
        
        if state["human_role"] == "被告律师":
            user_input = interrupt("请你就原告的说法进一步质疑，并努力论述自己的观点")
            return {"messages" : [HumanMessage(content=user_input, name = f"{self.name}({self.role})")],
                    "speaker" : "法官"
                    }
        else:
            model_input = [SystemMessage(content=ARGUE_PROMPT_DE)] + state["messages"]
            response = ds_V3.invoke(model_input)
            return {"messages" : [ChatMessage(content=response.content, name = f"{self.name}({self.role})", role = "assistant")],
                    "speaker" : "法官"
                    }