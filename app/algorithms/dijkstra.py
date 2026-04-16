"""
algorithms/dijkstra.py
=======================
Dijkstra's Algorithm – Academic Pathway Optimization

Finds the shortest (optimal) academic path through a curriculum graph of
14 courses, weighted by difficulty and prerequisite relationships.

The graph represents courses as nodes. Edge weights encode the relative
"cost" of transitioning between courses (difficulty step, prerequisite
completion burden). A lower total cost = smoother academic journey.

Time Complexity:  O((V + E) log V) with a min-heap  [V=nodes, E=edges]
Space Complexity: O(V + E)

Curriculum graph (14 courses, 3 tracks):
  STEM track   – Math → Physics → Chem → Bio → CompSci → Research
  Business     – Econ → Accounting → Management → Finance → Marketing
  Arts/Humanities – FilLit → Philosophy → Communications → CreativeArts
"""

import heapq

# ── Curriculum Graph ──────────────────────────────────────────────────────────
# Format: { node: [(neighbor, weight), ...] }
# Weight = difficulty step (1 = easy transition, 5 = hard transition)

CURRICULUM_GRAPH = {
    # STEM track
    'Math':       [('Physics', 2), ('CompSci', 2), ('Econ', 3)],
    'Physics':    [('Chem', 2), ('CompSci', 1), ('Research', 4)],
    'Chem':       [('Bio', 1), ('Research', 3)],
    'Bio':        [('Research', 2), ('Chem', 1)],
    'CompSci':    [('Research', 2), ('Math', 1), ('Management', 3)],
    'Research':   [],

    # Business track
    'Econ':       [('Accounting', 2), ('Management', 2), ('Finance', 3)],
    'Accounting': [('Finance', 1), ('Management', 2)],
    'Management': [('Finance', 1), ('Marketing', 2), ('CompSci', 3)],
    'Finance':    [('Marketing', 1), ('Research', 4)],
    'Marketing':  [('Research', 4), ('Communications', 2)],

    # Arts / Humanities track
    'FilLit':       [('Philosophy', 1), ('Communications', 2), ('CreativeArts', 2)],
    'Philosophy':   [('Communications', 1), ('Research', 4)],
    'Communications': [('CreativeArts', 1), ('Marketing', 2), ('Research', 3)],
    'CreativeArts': [('Research', 5), ('Marketing', 3)],
}

# All 14 courses in order
ALL_COURSES = [
    'Math', 'Physics', 'Chem', 'Bio', 'CompSci', 'Research',
    'Econ', 'Accounting', 'Management', 'Finance', 'Marketing',
    'FilLit', 'Philosophy', 'Communications', 'CreativeArts',
]

# Track entry points per interest
TRACK_STARTS = {
    'STEM':     'Math',
    'Business': 'Econ',
    'Arts':     'FilLit',
}

TRACK_GOAL = 'Research'   # All tracks converge toward Research / capstone


def dijkstra(graph: dict, start: str, goal: str) -> tuple[list, float]:
    """
    Run Dijkstra's algorithm on the curriculum graph.

    Parameters
    ----------
    graph : dict  – Adjacency list {node: [(neighbor, weight), ...]}
    start : str   – Starting course node
    goal  : str   – Target course node

    Returns
    -------
    (path, total_cost) – Ordered list of course names and total weight.
                         Returns ([], float('inf')) if no path exists.
    """
    # Min-heap: (cost, node)
    heap = [(0, start)]
    # Best known cost to each node
    dist = {node: float('inf') for node in graph}
    dist[start] = 0
    # Previous node on optimal path
    prev = {node: None for node in graph}

    while heap:
        current_cost, current = heapq.heappop(heap)

        if current == goal:
            break

        if current_cost > dist[current]:
            continue  # stale entry

        for neighbor, weight in graph.get(current, []):
            new_cost = current_cost + weight
            if new_cost < dist.get(neighbor, float('inf')):
                dist[neighbor] = new_cost
                prev[neighbor] = current
                heapq.heappush(heap, (new_cost, neighbor))

    # Reconstruct path
    if dist.get(goal, float('inf')) == float('inf'):
        return [], float('inf')

    path = []
    node = goal
    while node is not None:
        path.append(node)
        node = prev[node]
    path.reverse()
    return path, dist[goal]


def get_pathway(interests: list) -> dict:
    """
    Given a student's interest list, compute the optimal pathway
    for each matching track.

    Parameters
    ----------
    interests : list  – e.g. ['STEM', 'Business']

    Returns
    -------
    dict  – {track: {'path': [...], 'cost': float, 'start': str}}
    """
    results = {}
    if not interests:
        interests = list(TRACK_STARTS.keys())  # show all if none set

    for interest in interests:
        start = TRACK_STARTS.get(interest)
        if not start:
            continue
        path, cost = dijkstra(CURRICULUM_GRAPH, start, TRACK_GOAL)
        results[interest] = {
            'path':  path,
            'cost':  cost,
            'start': start,
            'goal':  TRACK_GOAL,
        }
    return results


def get_all_pathways() -> dict:
    """Return optimal pathways for all three tracks."""
    return get_pathway(list(TRACK_STARTS.keys()))


def get_course_description(course: str) -> str:
    descriptions = {
        'Math':           'Foundations of algebra, calculus, and statistics.',
        'Physics':        'Mechanics, thermodynamics, and electromagnetism.',
        'Chem':           'General chemistry and laboratory principles.',
        'Bio':            'Cellular biology, ecology, and life sciences.',
        'CompSci':        'Programming, data structures, and algorithms.',
        'Research':       'Capstone thesis / research methods.',
        'Econ':           'Micro and macroeconomic principles.',
        'Accounting':     'Financial accounting and bookkeeping.',
        'Management':     'Organizational behavior and management theory.',
        'Finance':        'Corporate finance and investment analysis.',
        'Marketing':      'Market research, branding, and consumer behavior.',
        'FilLit':         'Philippine literature and cultural studies.',
        'Philosophy':     'Logic, ethics, and critical thinking.',
        'Communications': 'Mass media, journalism, and public speaking.',
        'CreativeArts':   'Visual arts, design, and creative expression.',
    }
    return descriptions.get(course, course)
