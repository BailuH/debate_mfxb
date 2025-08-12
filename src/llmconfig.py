from dotenv import load_dotenv
from langchain_openai import ChatOpenAI

load_dotenv()

models = {
    "DeepSeek_V3" : ChatOpenAI(model= "DeepSeek-V3"),
    "DeepSeek_R1" : ChatOpenAI(model= "DeepSeek-R1")
}