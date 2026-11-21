from app.agents.graph import ask_assistant

question = "Show me all leave requests for EMP001"

print("\nEmployee Question:")
print(question)

answer = ask_assistant(question)

print("\nVeltrionyx AI Assistant:")
print(answer)