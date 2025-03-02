import numpy as np
import re
import asyncio
import asyncio
from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger
from metagpt.schema import Message
import json
from metagpt.environment import Environment
from metagpt.actions import Action, UserRequirement
from metagpt.roles import Role


class IdentifyRelevantAspect(Action):

    PROMPT_TEMPLATE : str = """
    Based on the provided Software Architecture Problem and the corresponding Architecture Design Decision, please identify and define no more than 6 most relevant and important aspects for choosing this decision.\n
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    Please note that the background knowledge may contain inaccuracies, so please verify and use it accordingly.\n
    Your output must be a list in the following format, without any other information:\n
    1. **aspect1**: aspect1_definition\n
    2. **aspect2**: aspect2_definition\n
    ...
    """

    name : str = "IdentifyRelevantAspect"

    async def run(self, architecture_problem: str, architecture_design_decision: str)->list[str]:
        prompt = self.PROMPT_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision)
        rsp = await self._aask(prompt)
        with open("rationale.txt", "a") as f:
            f.write("*"*10+"Identify Aspect"+"*"*10)
            f.write(rsp)
            f.write("\n")
            print("The analysis results of the Identifier have been written to the file!")
        relevant_aspect = IdentifyRelevantAspect.parse_relevant_aspect(rsp)
        print(relevant_aspect)
        return relevant_aspect

    @staticmethod
    def parse_relevant_aspect(rsp)->list[str]:
        pattern = re.compile(r'\d+\.\s["_*A-Za-z\s-]+:\s.*?(?=\d+\.\s["*A-Za-z\s-]+:|$)', re.DOTALL)
        matches = pattern.findall(rsp)
        points = [match.strip() for match in matches]
        return points
    
    
class AspectIdentifier(Role):
    name: str = "Agent1"
    profile: str = "AspectIdentifier"

    def __init__(self,**kwargs):
        super().__init__(**kwargs)
        self.set_actions([IdentifyRelevantAspect])
        self._watch([UserRequirement])

    async def _act(self):
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo  
        msg = self.rc.news[0]  
        msg_dict = json.loads(msg.content)
        relevant_aspect = await todo.run(msg_dict["architecture_problem"], msg_dict["architecture_design_decision"])

        for aspect in relevant_aspect:
            pattern = re.compile(r'(\d+)\.\s([_*A-Za-z\s-]+):\s(.*?)\s*(?=\d+\.|$)', re.DOTALL)
            match = pattern.search(aspect)
            result = {
                'aspect': match.group(2).strip(),
                'aspect_definition': match.group(3).strip(),
                'architecture_problem': msg_dict["architecture_problem"],
                'architecture_design_decision': msg_dict["architecture_design_decision"]
            }
            json_string = json.dumps(result, ensure_ascii=False, indent=4)
            self.rc.env.publish_message(Message(content=json_string, cause_by=IdentifyRelevantAspect))