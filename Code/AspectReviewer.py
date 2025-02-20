import numpy as np
import re
import asyncio
import json
import asyncio
from metagpt.actions import Action
from metagpt.roles import Role
from metagpt.context import Context
from metagpt.roles.product_manager import ProductManager
from metagpt.logs import logger
from metagpt.schema import Message
from AspectAnalyst import AnalyseAspect


class ReviewAspect(Action):

    PROMPT_TEMPLATE : str = """
    Here is a Software Architecture and its corresponding Architecture Design Decision below:\n
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    Please review the rationale of the design decision below from the perspective of {aspect}. \n
    "{aspect}: {aspect_rationale}"\n
    If the rationale is reasonable, your output should be like this:\n
    "Reasonable!"\n
    If the rationale is not reasonable or not rigorous enough., you should modify the rationale to make it reasonable. Your output should be like this:\n
    "Modified: 'your modified rationale'"\n 
    """
    name : str = "ReviewAspect"
    async def run(self, architecture_problem: str, architecture_design_decision: str, aspect: str, aspect_rationale: str):
        prompt = self.PROMPT_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision, aspect=aspect, aspect_rationale=aspect_rationale)
        rsp = await self._aask(prompt)
        relevant_aspect = ReviewAspect.parse_relevant_aspect(rsp)
        return relevant_aspect

    @staticmethod
    def parse_relevant_aspect(rsp):
        return rsp
    
    
class AspectReviewer(Role):
    name: str = "Agent4"
    profile: str = "AspectReviewer"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([ReviewAspect])
        self._watch([AnalyseAspect])

    async def _act(self):
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo     
        review_results = []
        for single_news in self.rc.news:
            msg_dict = json.loads(single_news.content)
            print("+"*10)
            print(msg_dict)
            print("+"*10)
            code_text = await todo.run(msg_dict["architecture_problem"], msg_dict["architecture_design_decision"], msg_dict["aspect"], msg_dict["aspect_rationale"])
            with open("C:\\Research\\LLMsForDesignProblem\\code\\formal_experiment\\AI_Agent\\rationale.txt", "a") as f:
                f.write("*"*20+"Review Aspect: ")
                f.write(msg_dict["aspect"]+"*"*20+"\n")
                f.write(code_text)
                f.write("\n")
                print("The analysis results of the Identifier have been written to the file!")
            review_result = AspectReviewer.parse_relevant_aspect(code_text)
            if review_result == "Reasonable!":
                review_results.append(msg_dict["aspect_rationale"])
            else:
                review_results.append(review_result)
        review_dict = {
            "architecture_problem": msg_dict["architecture_problem"],
            "architecture_design_decision": msg_dict["architecture_design_decision"],
            "review_result": review_results
        }
        self.rc.env.publish_message(Message(content=json.dumps(review_dict), cause_by=ReviewAspect))
    
    @staticmethod
    def parse_relevant_aspect(rsp):
        pattern = re.compile(r'Reasonable!', re.DOTALL)
        match = pattern.search(rsp)
        if match:
            return "Reasonable!"
        else:
            pattern = re.compile(r'Modified:\s*(.*)', re.DOTALL)
            match = pattern.search(rsp)
            if match:
                return match.group(1).strip()
            else:
                return rsp