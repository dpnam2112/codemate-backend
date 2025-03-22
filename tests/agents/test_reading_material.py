import asyncio
from agents.reading_material.agent import ReadingMaterialAgent
import nest_asyncio
nest_asyncio.apply()


agent = ReadingMaterialAgent()

async def main():
    print("========== TEST ===========")
    module_description = """
    Description: This module covers how operating systems manage processes, including process creation, execution, and termination. Students will learn about process scheduling, context switching, and inter-process communication (IPC).

    Objectives:
        - Understand how an OS creates and terminates processes.
        - Learn about different process states and transitions.
        - Explore process scheduling algorithms (e.g., Round Robin, Shortest Job First).
        - Implement basic process control in a simple simulation.
    """
    print("Module description:")
    print(module_description)

    response = await agent.generate_reading_material(
        module_description=module_description
    )
    print(response.model_dump())
    print("======= END OF TEST =========")

    print("========== TEST ===========")
    module_description = """
    Description: This module covers the implementation and use of linked lists, including singly and doubly linked lists. Students will learn to perform operations like insertion, deletion, and traversal.

    Objectives:

        Understand the structure and implementation of linked lists.

        Implement common linked list operations.

        Analyze the advantages and limitations of linked lists compared to arrays.
    """
    print("Module description:")
    print(module_description)

    response = await agent.generate_reading_material(
        module_description=module_description
    )
    print(response.model_dump())

    """
    {'reading_material': "# Understanding Linked Lists\n\nLinked lists are a foundational data structure in computer science. They are used to store collections of items in a way that provides dynamic memory allocation. This means we can grow and shrink the size of our list as needed, which is a significant advantage over arrays.\n\n## What is a Linked List?\nA linked list consists of a series of elements called nodes. Each node contains:\n- **Data**: Information or value the node holds.\n- **Pointer**: A reference (or link) to the next node in the sequence.\n\n### Types of Linked Lists\n1. **Singly Linked List**:\n   - Each node points to the next node.\n   - Example: Imagine a line of people where each person can only see the person directly in front.\n\n2. **Doubly Linked List**:\n   - Each node points to both the next and the previous node.\n   - Example: This is like a subway train where you can get off from both sides (forward and backward).\n\n### Key Operations on Linked Lists:\n1. **Insertion**: Adding a new node to the list. This can happen at the beginning, end, or at a specified position.\n   - Example: Adding a new student to the top of a class roster.\n\n2. **Deletion**: Removing a node from the list. It's important to update the pointers correctly to maintain the list structure.\n   - Example: Removing a student from the roster.\n\n3. **Traversal**: Accessing each node in the list to read or operate on the data.\n   - Example: Going through your class roster to check attendance.\n\n## Advantages of Linked Lists\n- **Dynamic Size**: Unlike arrays, linked lists can grow and shrink as needed.\n- **Efficient Insertions/Deletions**: Adding or removing nodes can be done without shifting elements, leading to better performance in certain scenarios.\n\n## Limitations of Linked Lists\n- **Memory Usage**: Each node requires more memory due to the storage of pointers.\n- **Sequential Access**: To access a particular item, you may need to traverse from the head, which can take time if the list is long.\n\n## Recap\nLinked lists are flexible data structures that enable efficient data management through nodes. They possess benefits such as dynamic sizing and ease of insertion/deletion but come with drawbacks like increased memory usage and slower access times compared to arrays.\n\n## Key Takeaways\n- Linked lists consist of nodes with data and pointers.\n- Singly and doubly linked lists have different structures and uses.\n- Common operations include insertion, deletion, and traversal.\n- There are pros and cons to using linked lists versus arrays.\n\n## Self-Assessment Prompts\n- Can you explain what a linked list is in your own words?\n- How would you visualize the process of inserting a new node into a linked list? \n\nRemember that understanding linked lists will help you in various programming and algorithm challenges!", 'questions': ['What are the components of a node in a linked list?', 'Explain the difference between a singly linked list and a doubly linked list.', 'Describe how to insert a node at the beginning of a singly linked list.', 'What happens to the pointers when you delete a node from a linked list?', 'Compare the advantages of linked lists over arrays based on memory and performance.', 'How would you design a program to keep track of students in a class using a linked list?']}
    """
    print("======= END OF TEST =========")
asyncio.run(main())
