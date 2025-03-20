INSERT INTO users (id, name, email, avatar_url, created_at, role, updated_at) VALUES
('317066c9-7c31-4b0a-90a1-04c5ca6e9c33', 'John Doe', 'johndoe@example.com', 'https://example.com/avatar/johndoe.png', NOW(), 'professor', NOW()),
('c9413c07-5e88-4f04-a3f5-21890b8ef053', 'Harry Potter', 'harrypotter@example.com', 'https://example.com/avatar/johndoe.png', NOW(), 'student', NOW());

INSERT INTO courses (id, name, professor_id, learning_outcomes, start_date, end_date, status, image_url, created_at, updated_at) VALUES 
('78bccebd-3eb1-4068-a786-0058323f0076', 'Introduction to Python', (SELECT id FROM users WHERE email = 'johndoe@example.com'), ARRAY['Understand basic Python syntax', 'Write simple Python scripts', 'Understand loops and conditionals'], NULL, NULL, 'new', NULL, NOW(), NOW());

INSERT INTO lessons (id, course_id, title, description, "order", learning_outcomes) VALUES
('d65af666-2742-4ca1-9c51-2d57aa483c37', '78bccebd-3eb1-4068-a786-0058323f0076', 'Python Basics', 'Learn the foundational syntax and structure of Python programming.', 1, ARRAY['Learn to declare and use variables', 'Understand Python''s basic syntax and structure', 'Identify and use different data types']),
('053d7d8f-b30a-4295-bd29-9370a805ccdf', '78bccebd-3eb1-4068-a786-0058323f0076', 'Control Flow', 'Understand decision-making in Python with conditional statements and loops.', 2, ARRAY['Learn the importance of proper indentation', 'Understand and implement loops', 'Write programs using conditional statements']),
('7bbc3089-d1fa-4a0e-964b-653ece200a5f', '78bccebd-3eb1-4068-a786-0058323f0076', 'Functions', 'Learn how to write reusable blocks of code with Python functions.', 3, ARRAY['Write reusable and modular code', 'Understand the purpose and structure of functions', 'Learn to use parameters and return values']),
('03099933-88d9-40f0-bcc7-516d4d88d3c4', '78bccebd-3eb1-4068-a786-0058323f0076', 'Data Structures', 'Explore Python''s built-in data structures for efficient data manipulation.', 4, ARRAY['Differentiate between mutable and immutable structures', 'Understand and use Python''s built-in data structures', 'Learn how to manipulate data with lists and dictionaries']),
('9adec80f-d867-47de-a889-a7b788ea9c13', '78bccebd-3eb1-4068-a786-0058323f0076', 'File Handling', 'Learn to read and write files using Python.', 5, ARRAY['Understand file modes and their purposes', 'Handle file-related errors', 'Open, read, and write files in Python']),
('486fc529-5bae-4fd9-9e90-af5d3f740061', '78bccebd-3eb1-4068-a786-0058323f0076', 'Error Handling', 'Handle errors gracefully in your Python programs.', 6, ARRAY['Learn to identify and handle exceptions', 'Write robust programs that handle edge cases', 'Use try-except blocks to manage errors']);

