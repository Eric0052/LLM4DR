import time
import asyncio
import json
import asyncio
import random
import faiss
import re
from metagpt.actions import Action
from metagpt.logs import logger
from metagpt.utils.common import OutputParser
from metagpt.roles.role import Role
from metagpt.schema import Message
from metagpt.tools.search_engine import SearchEngine
from pydantic import TypeAdapter, model_validator
from typing import Any, Callable, Optional, Union
from langchain_openai import OpenAIEmbeddings
from duckduckgo_search import DDGS
from langchain_community.vectorstores.faiss import FAISS
from langchain_community.docstore.in_memory import InMemoryDocstore
from AspectIdentifier import IdentifyRelevantAspect

embeddings_model = OpenAIEmbeddings()
embedding_size = 1536
index = faiss.IndexFlatL2(embedding_size)
shared_vectordb = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})

class CollectKnowledge(Action):
    PROMPT_TEMPLATE : str = """
    Here is a Software Architecture Problem and its corresponding Architecture Design Decision below:\n
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    "{aspect}": {aspect_definition}\n
    Please provide only 2 necessary keywords related to the Architecture Problem and its Design Decision from the perspective of "{aspect}" for search.
    Your response must be a list of keywords in the following format, without any other information:\n
    1. keywords1\n
    2. keywords2\n
    """

    RAG_TEMPLATE : str = """
    Architecture Problem: {architecture_problem}\n
    Architecture Design Decision: {architecture_design_decision}\n
    "{aspect}": {aspect_definition}\n
    ...
    """
    name : str = "CollectKnowledge"
    search_engine: Optional[SearchEngine] = None
    
    @model_validator(mode="after")
    def validate_engine_and_run_func(self):
        if self.search_engine is None:
            self.search_engine = SearchEngine.from_search_config(self.config.search, proxy="http://127.0.0.1:10809")
        return self

    def search_duckduckgo(self,query):
        bodies = []
        with DDGS() as ddgs:
            time.sleep(1)
            results = ddgs.text(query, max_results=20)
            results = [result for result in results if "stackoverflow" not in result["link"]]
            for result in results:
                body = result.get('body')
                if body:
                    bodies.append(body)
        return bodies

    async def run(self, architecture_problem: str, architecture_design_decision: str, aspect: str, aspect_definition:str)->list[str]:
        prompt = self.PROMPT_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision, aspect=aspect, aspect_definition=aspect_definition)
        rag = self.RAG_TEMPLATE.format(architecture_problem=architecture_problem, architecture_design_decision=architecture_design_decision, aspect=aspect, aspect_definition=aspect_definition)
        rsp = await self._aask(prompt)
        keywords = CollectKnowledge.parse_relevant_aspect(rsp)
        time.sleep(15)
        results = await asyncio.gather(*(self.search_engine.run(i, as_string=False) for i in keywords))
        embeddings_model = OpenAIEmbeddings()
        embedding_size = 1536
        index = faiss.IndexFlatL2(embedding_size)
        shared_vectordb = FAISS(embeddings_model.embed_query, index, InMemoryDocstore({}), {})
        context_knowledge_list = []
        for links in results:
            for link in links:
                context_knowledge_list.append(link["snippet"])
        for i, context_knowledge in enumerate(context_knowledge_list):
            if i>19:
                break
            shared_vectordb.add_texts(texts=[context_knowledge], ids=[i])
            print(f"Context knowledge {i} has been saved successfully.")
        similar_context = shared_vectordb.similarity_search(rag, 10)
        related_knowledge = []
        for context in similar_context:
            related_knowledge.append(context.page_content)
        return related_knowledge
    
    @staticmethod
    def parse_relevant_aspect(rsp)->list[str]:
        keywords = re.findall(r'\d+\.\s+(.*?)\s*$', rsp, re.MULTILINE)
        with open("rationale.txt", "a") as f:
            f.write("-"*20+"Extracted Keywords: ")
            for keyword in keywords:
                f.write(keyword + ", ")
            f.write("-" * 20 + "\n") 
            print("The keywords have been written to the file!！")

        return keywords

class InformationCollector(Role):
    name: str = "Agent2"
    profile: str = "InformationCollector"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_actions([CollectKnowledge])
        self._set_react_mode(react_mode="by_order")
        self._watch([IdentifyRelevantAspect])
        self.link_list: list[str]
        self.context_knowledge_list: list[str]

    async def _act(self):
        logger.info(f"{self._setting}: to do {self.rc.todo}({self.rc.todo.name})")
        todo = self.rc.todo
        for single_news in self.rc.news:
            msg_dict = json.loads(single_news.content)
            related_knowledge = await todo.run(msg_dict["architecture_problem"], msg_dict["architecture_design_decision"],msg_dict["aspect"],msg_dict["aspect_definition"])
            print("++++this is related knowledge++++")
            print(related_knowledge)
            print("++++this is related knowledge++++")
            knowledge_dict = {
                "architecture_problem": msg_dict["architecture_problem"],
                "architecture_design_decision": msg_dict["architecture_design_decision"],
                "aspect": msg_dict["aspect"],
                "aspect_definition": msg_dict["aspect_definition"],
                "knowledge": related_knowledge
            }
            json_string = json.dumps(knowledge_dict, ensure_ascii=False, indent=4)
            self.rc.env.publish_message(Message(content=json_string, cause_by=CollectKnowledge))