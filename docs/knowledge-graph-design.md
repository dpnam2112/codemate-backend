## The role of knowledge graph in adative learning

- There are a set of users and a set of concepts.
- There is a type/some types of relations to model the proficiency/mastery of the user against a specific concept.
E.g: There may be 4 types of relations: `-BEGINNER_AT->`, `-INTERMEDIATE_AT->`, `-ADVANCED_AT->`

## Ontology

### Nodes

- `User` node: Represents user/learner. Information includes:
    - id (UUID)

- A concept node contains the following information:
    - concept id (UUID) -> This is the surrogate key. Concepts are not only stored in the graph database, but also stored in the vector database for efficient retrieval.
    - concept name: Name of the concept. E.g: Fog Computing.
    - concept definition. E.g: The definition of 'Fog Computing' is: "is an architecture that uses edge devices to carry out a substantial amount of computation (edge computing), storage, and communication locally and routed over the Internet backbone."

- Document nodes: Represent the documents uploaded by teachers, instructors, .etc
- Course nodes: Represent the courses uploaded by the instructors.
- Lesson nodes: Represent the lessons created by the instructors.

## Relationships

- `(User) -[LEARN]-> (Concept)`: Determine if the learner has learned a specific concept. These relations contain an attribute `proficiency` to represent the proficiency/mastery of a user against a specific concept. There are 4 possible values: `BEGINNER`, `INTERMEDIATE`, `ADVANCED`.
- `(Course | Lesson | Document) -[COVER]-> (Concept)`: Determine if the learning resource cover the concept.
- `(Course) <-[BELONGS_TO]- (Lesson)`: Determine if the lesson belongs to the course.
- `(Course) <-[BELONGS_TO]- (Document)`: Determine if the document belongs to the course.

