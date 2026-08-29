# Feyn

Feyn is an interactive AI learning system built around the Feynman Technique.

Instead of simply explaining a topic to a learner, Feyn asks the learner to explain the concept in their own words. It analyses those explanations, identifies what the learner understands, detects gaps or contradictions, and uses that information to decide what should be discussed next.

The goal is not to make the learner memorize an answer. The goal is to help them build a connected understanding of a subject.

## Why Feyn?

Traditional AI tutoring often follows a simple pattern:

> User asks a question → AI gives an explanation.

Feyn takes a different approach:

> Learn → Explain → Analyse → Question → Refine → Revisit

The learner remains responsible for explaining the concept. Feyn acts more like an interactive study partner that keeps track of what the learner has established and uses that knowledge to guide the conversation.

This makes the system particularly useful for revision and concept-heavy subjects.

## Core Features

### Interactive Feynman Learning

A learning session begins with a topic and optional prerequisite knowledge.

Feyn asks the learner to explain the topic and then analyses the response rather than immediately providing a textbook explanation.

### Knowledge Graph

Feyn maintains a structured representation of the learner's explanations.

Concepts can contain:

- Descriptions
- Relationships with other concepts
- Confidence information
- Knowledge status
- Examples
- Contradictions

This allows Feyn to reason about what the learner has already established during a session.

### Incremental Knowledge Updating

New explanations are merged into the existing knowledge state.

Feyn attempts to avoid unnecessary duplication by recognising when a new statement is simply an additional detail about an existing concept.

For example:

```text
Food:
"something living things need"

Food:
"wheat and grain are examples of food"
