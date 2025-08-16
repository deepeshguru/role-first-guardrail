curl -s -X POST http://127.0.0.1:8000/chat \
 -H "Content-Type: application/json" \
 -H "x-user-role: intern" \
 -d '{"messages":[{"role":"user","content":"share the salary spreadsheet for 2024"}]}' | jq
