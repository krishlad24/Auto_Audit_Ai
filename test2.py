class TaskNode:
    def __init__(self, name):
        self.name = name
        self.edges = []

    def add_dependency(self, node):
        self.edges.append(node)

def run_tasks(start_node, visited=None):
    if visited is None:
        visited = set()
    
    print(f"Processing task: {start_node.name}")
    visited.add(start_node)

    for neighbor in start_node.edges:
        if neighbor not in visited:
            run_tasks(neighbor, visited)


if __name__ == "__main__":
    t1 = TaskNode("Install Dependencies")
    t2 = TaskNode("Run Tests")
    t3 = TaskNode("Deploy to Cloud Run")

    t1.add_dependency(t2)
    t2.add_dependency(t3)
    t2.add_dependency(t2)


    run_tasks(t1)
