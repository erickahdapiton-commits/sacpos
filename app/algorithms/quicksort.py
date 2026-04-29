"""
algorithms/quicksort.py
========================
QuickSort – Student Performance Ranking by GPA

Sorts students by GPA using the QuickSort algorithm.
Philippine GPA scale: 1.0 = best, 5.0 = worst.
Default sort order: ascending by GPA (best performers first).

Time Complexity:  O(n log n) average, O(n²) worst case
Space Complexity: O(log n) average (recursion stack)
"""


def quicksort_students(students: list, key: str = 'gpa',
                       descending: bool = False) -> list:
    """
    Sort a list of Student objects by a given key using QuickSort.

    Parameters
    ----------
    students   : list  – List of Student model objects
    key        : str   – Attribute name to sort by ('gpa', 'attendance', 'full_name')
    descending : bool  – If True, sort highest first (for attendance/scores).
                         For GPA: ascending = best first (1.0 is best).

    Returns
    -------
    list – New sorted list (does not mutate original)
    """
    arr = list(students)
    _quicksort(arr, 0, len(arr) - 1, key)
    if descending:
        arr.reverse()
    return arr


def _quicksort(arr: list, low: int, high: int, key: str):
    if low < high:
        pivot_idx = _partition(arr, low, high, key)
        _quicksort(arr, low, pivot_idx - 1, key)
        _quicksort(arr, pivot_idx + 1, high, key)


def _partition(arr: list, low: int, high: int, key: str) -> int:
    pivot_val = _get_key(arr[high], key)
    i = low - 1
    for j in range(low, high):
        if _get_key(arr[j], key) <= pivot_val:
            i += 1
            arr[i], arr[j] = arr[j], arr[i]
    arr[i + 1], arr[high] = arr[high], arr[i + 1]
    return i + 1


def _get_key(student, key: str):
    val = getattr(student, key, 0)
    if isinstance(val, str):
        return val.lower()
    return val if val is not None else 0


def rank_students(students: list) -> list:
    """
    Rank students by GPA (Philippine scale: 1.0 = rank 1).
    Returns list of (rank, student) tuples.
    """
    sorted_students = quicksort_students(students, key='gpa', descending=False)
    return [(i + 1, s) for i, s in enumerate(sorted_students)]
