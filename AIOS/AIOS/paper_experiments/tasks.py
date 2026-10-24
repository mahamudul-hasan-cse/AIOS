"""Fixed, checkable task set for the AgentOS vs. no-kernel comparison.

Each task is a natural-language coding request (the pipeline's `topic`) plus a
deterministic success check: the generated script, run in the sandbox, must
print a line containing `expect`. Nothing here depends on the LLM backend.
"""
TASKS = [
    {"id": "T01", "topic": "Write a Python script that prints the sum of the integers from 1 to 100.", "expect": "5050"},
    {"id": "T02", "topic": "Write a Python script that prints the 20th Fibonacci number, where fib(1)=1 and fib(2)=1.", "expect": "6765"},
    {"id": "T03", "topic": "Write a Python script that prints the factorial of 10.", "expect": "3628800"},
    {"id": "T04", "topic": "Write a Python script that prints how many prime numbers are below 100.", "expect": "25"},
    {"id": "T05", "topic": "Write a Python script that reverses the string 'agentos' and prints the result.", "expect": "sotnega"},
    {"id": "T06", "topic": "Write a Python script that prints the greatest common divisor of 462 and 1071.", "expect": "21"},
    {"id": "T07", "topic": "Write a Python script that counts the vowels in the sentence 'operating systems govern agents' and prints the count.", "expect": "9"},
    {"id": "T08", "topic": "Write a Python script that prints the list [5, 3, 9, 1, 7] sorted in ascending order.", "expect": "[1, 3, 5, 7, 9]"},
    {"id": "T09", "topic": "Write a Python script that prints the sum of the squares of the integers from 1 to 10.", "expect": "385"},
    {"id": "T10", "topic": "Write a Python script that prints the binary representation of 37 without the 0b prefix.", "expect": "100101"},
    {"id": "T11", "topic": "Write a Python script that checks whether 'racecar' is a palindrome and prints True or False.", "expect": "True"},
    {"id": "T12", "topic": "Write a Python script that prints the largest number in the list [12, 45, 7, 89, 23].", "expect": "89"},
]


def check(task, stdout: str) -> bool:
    return task["expect"] in (stdout or "")
