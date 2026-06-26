 3. Test Basic Redux Connectivity

  Run this from the CLI folder so it loads the same .env values:

  node dist/cli.js generate --help

  This only verifies the CLI is executable.

  Then test the Redux converse endpoint with curl. Replace values manually from .env:

  curl -s \
    -X POST "$BASE_URL/api/ai/bedrock/converse" \
    -H "Content-Type: application/json" \
    -H "token: $API_KEY" \
    -d '{
      "modelId": "'"$MODEL_ID"'",
      "projectId": "'"$PROJECT_ID"'",
      "threadId": "redux-odm-smoke-test",
      "system": [
        {
          "text": "You are a concise test assistant. Reply with OK only."
        }
      ],
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "text": "Connectivity test"
            }
          ]
        }
      ],
      "inferenceConfig": {
        "maxTokens": 20,
        "temperature": 0,
        "topP": 0.1
      }
    }'

  Expected response should contain something like:

  {
    "output": {
      "message": {
        "content": [
          {
            "text": "OK"
          }
        ]
      }
    }
  }

  If you get 401 or 403, the API key/token is wrong or expired.

  If you get 404, check BASE_URL.

  If you get model/provider errors, check MODEL_ID and Redux backend LLM config.

  4. Test Prompt Cache Compatibility

  Use this only if PROMPT_CACHE=true:

  curl -s \
    -X POST "$BASE_URL/api/ai/bedrock/converse" \
    -H "Content-Type: application/json" \
    -H "token: $API_KEY" \
    -d '{
      "modelId": "'"$MODEL_ID"'",
      "projectId": "'"$PROJECT_ID"'",
      "threadId": "redux-odm-cache-test",
      "system": [
        {
          "text": "Stable system prompt for cache test."
        },
        {
          "cachePoint": {
            "type": "default"
          }
        }
      ],
      "messages": [
        {
          "role": "user",
          "content": [
            {
              "text": "Reply OK"
            }
          ]
        }
      ],
      "inferenceConfig": {
        "maxTokens": 20,
        "temperature": 0,
        "topP": 0.1
      }
    }'

  If this fails but the previous curl succeeds, set:

  PROMPT_CACHE=false

  5. Dry Help Check For ODM Command

  node dist/cli.js generate --help

  You should see:

  --workspace
  --rule-project
  --out
  --package
  --rules-folder
  --max-files-per-request
  --max-shared-chars
  --max-file-chars

  6. Run One Small Package First

  Start with one package, not the full 950-rule project:

  node dist/cli.js generate \
    --workspace /path/to/client-odm-repo \
    --rule-project path/to/ruleproject \
    --package path/to/ruleproject/rules/somePackage \
    --max-files-per-request 3 \
    --max-shared-chars 15000 \
    --max-file-chars 5000

  Expected output:

  [redux-odm] package ... all (...)
  [redux-odm] complete: wrote 2 files

  Generated files go to:

  /path/to/client-odm-repo/out/manual-llm-rule-requirements/responses/rules

  7. Run One Folder/Subtree

  After one package works:

  node dist/cli.js generate \
    --workspace /path/to/client-odm-repo \
    --rule-project path/to/ruleproject \
    --rules-folder path/to/ruleproject/rules/someFolder \
    --max-files-per-request 5 \
    --max-shared-chars 20000 \
    --max-file-chars 6000

  You can also try short selector:

  --rules-folder someFolder

  8. Run Full Client Project

  Only after package and folder tests pass:

  node dist/cli.js generate \
    --workspace /path/to/client-odm-repo \
    --rule-project path/to/ruleproject \
    --max-files-per-request 5 \
    --max-shared-chars 20000 \
    --max-file-chars 6000

  For 950 rules, I would start with --max-files-per-request 5, not the default 8, until we see output quality and latency.
