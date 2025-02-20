import numpy as np
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from AspectIdentifier import IdentifyRelevantAspect
from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger
from metagpt.schema import Message
from InformationCollector import shared_vectordb
import json
from InformationCollector import CollectKnowledge


class AnalyseAspect(Action):

    PROMPT_TEMPLATE : str = """
    Here is a Software Architecture Problem and its corresponding Architecture Design Decision below:\n
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    Please analyze and provide the Design Rationale for this decision from the perspective of {aspect}. The definition of {aspect} is as follows:\n
    {aspect}:{aspect_definition}\n
    You may refer to the following information:\n
    {knowledge}\n
    Your output should be like this:\n
    "From the perspective of {aspect}, the rationale of this Design Decision is that ....."
    """

    name : str = "IdentifyRelevantAspect"

    async def run(self, architecture_problem: str, architecture_design_decision: str, aspect: str, aspect_definition: str,knowledge:str):
        prompt = self.PROMPT_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision, aspect=aspect, aspect_definition=aspect_definition, knowledge=knowledge)
        rsp = await self._aask(prompt)
        return rsp

    @staticmethod
    def parse_relevant_aspect(rsp):
        return rsp
    
    
class AspectAnalyst(Role):
    name: str = "Agent3"
    profile: str = "AspectAnalyst"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([AnalyseAspect])
        self._watch([CollectKnowledge])

    async def _act(self):
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        for single_news in self.rc.news:
            msg_dict = json.loads(single_news.content)
            knowledge_str = "\n".join(msg_dict["knowledge"])
            code_text = await todo.run(msg_dict["architecture_problem"], msg_dict["architecture_design_decision"], msg_dict["aspect"], msg_dict["aspect_definition"],knowledge_str)
            with open("ationale.txt", "a") as f:
                f.write("*"*20+"Aspect: ")
                f.write(msg_dict["aspect"]+"*"*20+"\n")
                f.write(code_text)
                f.write("*"*20)
                f.write("\n"*2)
            rationale_dict = {
                "architecture_problem": msg_dict["architecture_problem"],
                "architecture_design_decision": msg_dict["architecture_design_decision"],
                "aspect": msg_dict["aspect"],
                "aspect_definition": msg_dict["aspect_definition"],
                "aspect_rationale": code_text
            }
            json_string = json.dumps(rationale_dict, ensure_ascii=False, indent=4)
            self.rc.env.publish_message(Message(content=json_string, cause_by=AnalyseAspect))