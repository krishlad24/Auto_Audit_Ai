class TaskNode:
    def __init__(self, name):
        self.name = name
        self.edges = []

    def add_dependency(self, node):
        # SMELL: No check for circular dependencies
        self.edges.append(node)

def run_tasks(start_node, visited=None):
    if visited is None:
        visited = set()
    
    # SMELL: Potential RecursionError for very deep graphs
    # SMELL: Inefficient print debugging instead of logging
    print(f"Processing task: {start_node.name}")
    visited.add(start_node)

    for neighbor in start_node.edges:
        if neighbor not in visited:
            run_tasks(neighbor, visited)

# Testing the implementation
if __name__ == "__main__":
    t1 = TaskNode("Install Dependencies")
    t2 = TaskNode("Run Tests")
    t3 = TaskNode("Deploy to Cloud Run")

    t1.add_dependency(t2)
    t2.add_dependency(t3)

    # Triggering the logic
    run_tasks(t1)
