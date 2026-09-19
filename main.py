class Agent():
    project_id: str
    thread_id: str
    tools = []



class Worker(Agent):
    pass


class Coordinator(Agent):
    pass


class Secretar(Agent):
    pass


class Imitator(Agent):
    pass




coordinator = Agent(
    tools=[tasks],
    prompt=coordinator_prompt,
)

imitator = Agent(
    tools=[],
    prompt=imitator_prompt
)

coordinator.listen(message.to)

orchestrator = Orchestrator(coordinator, imitator)


test_case1 = Workspace(coordinator, imitator)