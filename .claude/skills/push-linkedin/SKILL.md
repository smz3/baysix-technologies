# Skill: push-linkedin

Generate and review a LinkedIn post about recent Baysix progress, then await approval before publishing.

## Usage
```
/push-linkedin [optional: topic or content to feature]
```

## Steps

1. Navigate to sigma-linkedin:
   ```
   cd C:\Users\User\Desktop\sigma-linkedin
   ```

2. Read the config to understand what projects are analyzed:
   - `config.yaml` — project paths for analyzer

3. Run the analyzer to generate post content:
   ```bash
   python main.py
   ```
   Or if a specific topic is requested, pass it as context to the writer agent directly.

4. Read the generated post from `posts.log` or stdout

5. **STOP — present the post to the user for review:**
   ```markdown
   ## Proposed LinkedIn Post

   [full post content here]

   ---
   Character count: [N]
   Estimated reach: [based on past posts if available]

   [REQUIRES APPROVAL] — Reply "approve" to publish, or provide edits.
   ```

6. Only after explicit user approval:
   - Run the publish command (if LinkedIn API is connected)
   - Or instruct the user to copy-paste manually
   - Log the published post in `posts.log`

## Notes
- **Never auto-publish** — always require explicit user approval
- If LinkedIn API token is expired (`token.txt`), alert the user to re-authenticate
- Keep posts professional and data-driven — Baysix is a quantitative fund, not a lifestyle brand
- Respect rate limits — do not attempt to post more than once per 24 hours
