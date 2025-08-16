curl -s -X POST http://127.0.0.1:8000/chat \
 -H "Content-Type: application/json" \
 -H "x-user-role: hr_manager" \
 -H "x-user-orgunit: HR" \
 -H "x-user-geo: IN" \
 -d '{"messages":[{"role":"user","content":"payroll summary for IN market"}]}' | jq
