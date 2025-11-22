# Conversation History & Context Improvements

## Problem Solved
The assistant can now handle follow-up questions like:
- **User:** "What are places I can go in London?"
- **Assistant:** *Shows 8 places*
- **User:** "Suggest some more"
- **Assistant:** *Shows 8 NEW places that weren't shown before*

## Changes Made

### 1. **Chat History Retrieval** (`base_repo.py`)
- Added `get_chat_history()` method to retrieve the last 10 messages
- Returns messages in chronological order for context

### 2. **Context-Aware Location Extraction** (`llm_connection.py`)
- Added `extract_location_with_context()` method
- Uses previous conversation to understand references like:
  - "there"
  - "suggest some more"
  - "what else"
  - "show me other places"

### 3. **Context-Aware Intent Classification** (`llm_connection.py`)
- Added `classify_intent_with_context()` method
- Understands that "suggest some more" after places = PLACES intent
- Passes last 3 messages for context

### 4. **Smart Place Filtering** (`Parent_service.py`)
- Tracks which places were shown in previous messages
- Filters out already-shown places
- Shows up to 8 new places on each request
- Fetches 30 places from API to ensure variety

### 5. **Follow-up Detection & Response** (`Parent_service.py`)
- Detects follow-up keywords: "more", "else", "other", "another", "additional"
- Uses different phrasing for follow-ups:
  - First request: "In London these are the places you can go:"
  - Follow-up: "Here are some more places you can visit in London:"

## How It Works

### Flow for Follow-up Questions:
```
User: "Show me places in London"
  ↓
1. Retrieve chat history (empty)
2. Extract location: "London"
3. Classify intent: PLACES
4. Fetch 30 places from API
5. Show first 8 places
6. Save to chat history

User: "Suggest some more"
  ↓
1. Retrieve chat history (previous conversation)
2. Extract location with context: "London" (from history)
3. Classify intent with context: PLACES
4. Fetch places (from cache)
5. Filter out 8 already shown places
6. Show 8 new places
7. Save to chat history
```

## Example Conversations

### Example 1: Follow-up Places
```
User: "What are places to visit in Paris?"
Bot: "In Paris these are the places you can go:
- Eiffel Tower
- Louvre Museum
- Arc de Triomphe
..."

User: "Show me more"
Bot: "Here are some more places you can visit in Paris:
- Notre-Dame Cathedral
- Sacré-Cœur
- Versailles
..."
```

### Example 2: Context Understanding
```
User: "I'm going to Tokyo, what's the weather?"
Bot: "In Tokyo it's currently 18°C with Clear sky."

User: "What places can I visit there?"
Bot: "In Tokyo these are the places you can go:
- Senso-ji Temple
- Tokyo Skytree
- Meiji Shrine
..."
```

### Example 3: Combined Follow-up
```
User: "Plan my trip to Mumbai"
Bot: "In Mumbai it's currently 28°C with Clear sky.

And these are the places you can go:
- Gateway of India
- Marine Drive
..."

User: "Any other attractions?"
Bot: "Here are some more places you can visit in Mumbai:
- Elephanta Caves
- Juhu Beach
- Haji Ali Dargah
..."
```

## Technical Details

### Database Schema
Chat history stored in `chats` collection:
```json
{
  "session_id": "abc-123",
  "user_message": "Show me places in London",
  "bot_response": "In London these are the places you can go:\n- Big Ben\n- Tower of London",
  "timestamp": "2025-11-22T10:30:00Z"
}
```

### LLM Context Window
- Location extraction: Uses last 5 messages
- Intent classification: Uses last 3 messages
- Keeps context focused and reduces token usage

## Benefits

✅ **Natural Conversations** - Users can ask follow-up questions naturally
✅ **Context Awareness** - Understands references to previous locations
✅ **No Duplicates** - Shows different places on each request
✅ **Scalable** - Works with unlimited follow-ups until places run out
✅ **Smart Fallbacks** - Falls back gracefully if context fails
