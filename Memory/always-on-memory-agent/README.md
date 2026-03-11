# Always-On Memory Agent

This agent demonstrates how to implement a persistent memory system for Gemini-based agents using local file storage. It includes a chat interface and a separate dashboard to inspect the agent's "subconscious" (stored memory).

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Set your Google API Key:
   ```bash
   export GOOGLE_API_KEY='your-key-here'
   ```

3. Run the agent:
   ```bash
   streamlit run agent.py
   ```

4. Run the dashboard:
   ```bash
   streamlit run dashboard.py
   ```
