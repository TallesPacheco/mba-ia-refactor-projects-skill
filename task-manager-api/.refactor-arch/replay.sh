#!/bin/bash
# Validação da Fase 3: repete as 63 requisições do baseline.md, agora com as credenciais
# (Authorization: Bearer <token do login> e X-Admin-Token) e checa 401/403 sem elas.
# Uso: PORT=<porta> bash .refactor-arch/replay.sh
B="http://127.0.0.1:${PORT:?}"
ADM='X-Admin-Token: dev-admin-token'
n=0

req() { # req <method> <path> [json] [extra-header]
  n=$((n+1))
  local m="$1" p="$2" body="$3" hdr="$4"
  local args=(-s -o /tmp/_v.json -w '%{http_code}|%{content_type}' -X "$m" "$B$p")
  [ -n "$body" ] && args+=(-H 'Content-Type: application/json' -d "$body")
  [ -n "$hdr" ] && args+=(-H "$hdr")
  local out; out=$(curl "${args[@]}")
  echo "### $n | $m $p | payload=${body:-"-"} | hdr=${hdr:-"-"} | HTTP ${out}"
  head -c 1200 /tmp/_v.json; echo
}

token_for() { # token_for <email> <senha>
  curl -s -X POST "$B/login" -H 'Content-Type: application/json' \
    -d "{\"email\":\"$1\",\"password\":\"$2\"}" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p'
}

T_JOAO=$(token_for joao@email.com "${SEED_ADMIN_PASSWORD:-1234}")
T_MARIA=$(token_for maria@email.com "${SEED_USER_PASSWORD:-abcd}")
echo "token joao (id 1): ${T_JOAO:0:24}... (len ${#T_JOAO})"
echo "token maria (id 2): ${T_MARIA:0:24}... (len ${#T_MARIA})"
AJ="Authorization: Bearer $T_JOAO"
AM="Authorization: Bearer $T_MARIA"

# --- leituras públicas ---
req GET /
req GET /health
req GET /tasks
req GET /tasks/1
req GET /tasks/999
req GET '/tasks/search?q=API'
req GET '/tasks/search?status=pending&priority=1'
req GET '/tasks/search?priority=abc'
req GET /tasks/stats
# --- leituras com PII: 401 sem credencial, 200 com, 403 de outro usuário ---
req GET /users
req GET /users '' "$AJ"
req GET /users/1
req GET /users/1 '' "$AJ"
req GET /users/1 '' "$AM"
req GET /users/999 '' "$ADM"
req GET /users/1/tasks '' "$AJ"
req GET /users/999/tasks '' "$ADM"
req GET /reports/summary
req GET /reports/summary '' "$AJ"
req GET /reports/user/1 '' "$AJ"
req GET /reports/user/1 '' "$AM"
req GET /reports/user/999 '' "$ADM"
req GET /categories
req GET /__rota-inexistente__
req POST /__rota-inexistente__ '{}'
req DELETE /tasks '{}'

# --- login ---
req POST /login "{\"email\":\"joao@email.com\",\"password\":\"${SEED_ADMIN_PASSWORD:-1234}\"}"
req POST /login '{"email":"joao@email.com","password":"x"}'
req POST /login '{}'

# --- criações ---
req POST /tasks '{"title":"Nova task baseline","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2026-12-01","tags":["a","b"]}'
req POST /tasks '{"title":"Nova task baseline","description":"d","priority":2,"user_id":1,"category_id":1,"due_date":"2026-12-01","tags":["a","b"]}' "$AJ"
req POST /tasks '{"title":"ab"}' "$AJ"
req POST /tasks '{"title":"Prioridade str","priority":"2"}' "$AJ"
req POST /tasks '{"title":"user ruim","user_id":999}' "$AJ"
req POST /tasks '{"title":"tipo dict","user_id":{"a":1}}' "$AJ"
req POST /tasks '{"title":"tipo lista","user_id":[1]}' "$AJ"
req POST /users '{"name":"Ana","email":"ana@email.com","password":"segredo"}'
req POST /users '{"name":"Ana","email":"ana@email.com","password":"segredo"}'
req POST /users '{"name":"X","email":"bad","password":"segredo"}'
req POST /users '{"name":"Root","email":"root@email.com","password":"segredo","role":"admin"}'
req POST /users '{"name":"Root","email":"root@email.com","password":"segredo","role":"admin"}' "$ADM"
req POST /categories '{"name":"QA","color":"#ffffff"}'
req POST /categories '{"name":"QA","color":"#ffffff"}' "$AJ"
req POST /categories '{}' "$AJ"

T_ANA=$(token_for ana@email.com segredo)
AA="Authorization: Bearer $T_ANA"
echo "token ana (id 4): ${T_ANA:0:24}... (len ${#T_ANA})"

# --- atualizações ---
req PUT /tasks/11 '{"status":"done","title":"Nova task atualizada"}'
req PUT /tasks/11 '{"status":"done","title":"Nova task atualizada"}' "$AJ"
req PUT /tasks/11 '{"status":"xx"}' "$AJ"
req PUT /tasks/999 '{"status":"done"}' "$AJ"
req PUT /tasks/1 '{"description":{"x":1}}' "$AJ"
req PUT /users/4 '{"name":"Ana Maria","role":"manager"}'
req PUT /users/4 '{"name":"Ana Maria","role":"manager"}' "$AA"
req PUT /users/4 '{"name":"Ana Maria","role":"manager"}' "$ADM"
req PUT /users/4 '{"role":"root"}' "$ADM"
req PUT /users/4 '{"name":"Ana Only"}'
req PUT /users/4 '{"name":"Ana Only"}' "$AM"
req PUT /users/4 '{"name":"Ana Only"}' "$AA"
req PUT /users/1 '{"password":"invadido123"}'
req POST /login '{"email":"joao@email.com","password":"invadido123"}'
req PUT /users/999 '{"name":"x"}' "$ADM"
req PUT /categories/5 '{"name":"QA2"}'
req PUT /categories/5 '{"name":"QA2"}' "$AJ"
req PUT /categories/999 '{"name":"x"}' "$AJ"
n=$((n+1)); out=$(curl -s -o /tmp/_v.json -w '%{http_code}|%{content_type}' -X PUT "$B/categories/5" -H "$AJ" -d 'x'); echo "### $n | PUT /categories/5 | payload=sem Content-Type | hdr=Bearer | HTTP ${out}"; head -c 300 /tmp/_v.json; echo
req PUT /categories/5 'null' "$AJ"

# --- task da Ana, depois deleções ---
req POST /tasks '{"title":"Task da Ana","user_id":4}' "$AJ"
req DELETE /tasks/11
req DELETE /tasks/11 '' "$AJ"
req DELETE /tasks/11 '' "$ADM"
req DELETE /tasks/999 '' "$ADM"
req GET /tasks/12
req DELETE /users/4
req DELETE /users/4 '' "$ADM"
req GET /tasks/12
req DELETE /users/999 '' "$ADM"
req DELETE /categories/5
req DELETE /categories/5 '' "$ADM"
req DELETE /categories/999 '' "$ADM"
req DELETE /categories/4 '' "$ADM"
req GET /tasks/4
req DELETE /users/5 '' "$ADM"
echo "TOTAL REQUESTS: $n"
