from solution import Solution

TOKEN = "1153e179bbb8d48ddd72e9f8c452c2bb"
BASE_URL = "http://hw1.alexbers.com"

if __name__ == "__main__":
    solver = Solution(BASE_URL, TOKEN)
    solver.run()