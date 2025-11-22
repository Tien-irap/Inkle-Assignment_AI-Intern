# Testing Guide - Travel Assistant AI

## 📚 Table of Contents
1. [Architecture & State Management](#architecture--state-management)
2. [Manual Testing Guide](#manual-testing-guide)
3. [API Testing](#api-testing)
4. [Database Testing](#database-testing)
5. [Docker Testing](#docker-testing)
6. [Load Testing](#load-testing)

---

## 🏗️ Architecture & State Management

### Problem Solved

**Before (LLM Context):**
- ❌ LLM reads chat history to find location
- ❌ "What's the weather in Mumbai?" after Paris discussion → LLM confused
- ❌ Hallucination: combines locations or misses context
- ❌ Unreliable: depends on LLM understanding conversation flow

**After (State Management):**
- ✅ Deterministic state stored in MongoDB per session
- ✅ "What's the weather in Mumbai?" → Updates `current_location = Mumbai`
- ✅ "What's the weather there?" → Reads `current_location` from state
- ✅ No hallucination: simple variable read/write

### State Schema

```python
ConversationState = {
    # Location context (persistent)
    "current_location": "Paris",      # Last mentioned city
    "current_lat": 48.8566,          # Geocoded latitude
    "current_lon": 2.3522,           # Geocoded longitude
    
    # Place tracking (persistent)
    "shown_places": [                # All places shown to user
        "Eiffel Tower",
        "Louvre Museum",
        ...
    ],
    
    # Transient (per request)
    "user_message": "...",           # Current message
    "intent": "WEATHER",             # Current intent
    "response_text": "...",          # Response to return
    "weather_data": {...},           # Weather info
    "places_data": [...]             # Places list
}
```

### State Lifecycle

#### 1. Load State (Session Start)
```python
session_state = await state_manager.get_state(session_id)
# Returns existing state or creates new with defaults
```

#### 2. Update State (Location Mentioned)
```python
# User: "Weather in Paris"
extracted = "Paris"  # From LLM extraction

# UPDATER LOGIC
await state_manager.update_location(
    session_id,
    location="Paris",
    lat=48.8566,
    lon=2.3522
)
# State now: current_location = "Paris"
```

#### 3. Read State (Context Reference)
```python
# User: "What's the weather there?"
extracted = None  # No location in current message

# READER LOGIC
location = session_state.get("current_location")  # "Paris"
# Use Paris without asking LLM to interpret "there"
```

#### 4. Persist State (Throughout Session)
```python
# State stays in MongoDB until:
# - New location mentioned (update)
# - Session cleared (manual reset)

# 10 messages later...
# User: "Suggest some places"
location = session_state.get("current_location")  # Still "Paris"!
```

### Comparison: LLM Context vs State Management

**Chat Flow:**
1. User: "Weather in Paris"
2. User: "Suggest places to visit"
3. User: "Weather in Mumbai"
4. User: "What's the weather there?"

#### LLM Context Approach:
```
1. LLM extracts: Paris ✅
2. LLM sees history, uses: Paris ✅
3. LLM extracts: Mumbai ✅
4. LLM looks at history:
   - Sees "Paris" (2 messages ago)
   - Sees "Mumbai" (1 message ago)
   - Might return: "Mumbai" ✅
   - Might return: "Paris" ❌ (confusion)
   - Might return: "NONE" ❌ (hallucination)
```

#### State Management Approach:
```
1. Extract: Paris → STATE = {location: "Paris"} ✅
2. Extract: None → Read STATE.location = "Paris" ✅
3. Extract: Mumbai → STATE = {location: "Mumbai"} ✅
4. Extract: None → Read STATE.location = "Mumbai" ✅
   DETERMINISTIC - always correct!
```

### Key Components

#### SessionStateManager (`session_state.py`)
- Loads state from MongoDB
- Updates location/places
- Persists changes
- No LLM involved

#### Modified Parent_service (`Parent_service.py`)
```python
# OLD: Chat history lookup
chat_history = await repo.get_chat_history(session_id)
location = llm.extract_with_context(message, chat_history)  # ❌ Unreliable

# NEW: State-based
session_state = await state_manager.get_state(session_id)
if extracted_location:
    await state_manager.update_location(...)  # Update
else:
    location = session_state["current_location"]  # Read
```

#### Place Tracking
```python
# OLD: Parse chat history for place names
for chat in history:
    bot_msg = chat["response"]
    # Extract place names with regex...  # ❌ Fragile

# NEW: State-based set
shown_places = session_state.get("shown_places", [])
new_places = [p for p in all_places if p not in shown_places]
await state_manager.add_shown_places(session_id, new_places)
```

### MongoDB Schema

**Collection:** `conversation_states`

```javascript
{
  "_id": ObjectId("..."),
  "session_id": "abc-123-def",
  "current_location": "Paris",
  "current_lat": 48.8566,
  "current_lon": 2.3522,
  "shown_places": [
    "Eiffel Tower",
    "Louvre Museum",
    "Arc de Triomphe",
    ...
  ],
  "updated_at": ISODate("2025-11-22T19:00:00Z")
}
```

### Benefits

1. **Deterministic**: State read/write, no LLM interpretation
2. **Persistent**: Survives multiple messages, even server restarts
3. **Simple**: Direct variable access, no parsing
4. **Fast**: No LLM call for context understanding
5. **Reliable**: No hallucination or context confusion
6. **Testable**: Easy to verify state updates

---

## 🧪 Manual Testing Guide

### Prerequisites
- Application running (either via Docker or locally)
- Frontend accessible at http://localhost:8501
- Backend accessible at http://localhost:8000

---

## Test Scenarios

### 1. Basic Location Extraction

#### Test 1.1: Direct Location Query - Weather
**Input:** `What is the weather in Paris?`

**Expected:**
- ✅ Location extracted: Paris
- ✅ Intent: WEATHER
- ✅ Response includes: temperature, feels like, humidity, wind speed, rain probability
- ✅ Weekly summary displayed
- ✅ State updated: `current_location = "Paris"`

#### Test 1.2: Direct Location Query - Places
**Input:** `Show me places to visit in Tokyo`

**Expected:**
- ✅ Location extracted: Tokyo
- ✅ Intent: PLACES
- ✅ Response includes: 8 tourist attractions (museums, landmarks, monuments)
- ✅ No hotels or restaurants in suggestions
- ✅ Place names in English for international cities
- ✅ State updated: `current_location = "Tokyo"`, `shown_places = [...]`

#### Test 1.3: Direct Location Query - Both
**Input:** `Plan my trip to London`

**Expected:**
- ✅ Location extracted: London
- ✅ Intent: BOTH
- ✅ Response includes: weather information + place suggestions
- ✅ State updated with London location and places

---

### 2. State-Based Context Handling

#### Test 2.1: Context Using State - Places
**Steps:**
1. First query: `Show me places to visit in Paris`
2. Follow-up: `Suggest some more places`

**Expected:**
- ✅ First query: Location = Paris extracted, STATE updated
- ✅ Follow-up: No location extracted, reads STATE (`current_location = "Paris"`)
- ✅ 8 NEW places shown (no duplicates from first response)
- ✅ Log shows: "Using location from STATE: Paris"
- ✅ Log shows: "Found X previously shown places in STATE"

#### Test 2.2: Context Using State - Weather
**Steps:**
1. First query: `Show me places in Mumbai`
2. Follow-up: `What is the weather there?`

**Expected:**
- ✅ First query: Mumbai extracted and stored in STATE
- ✅ Follow-up: Reads `current_location` from STATE (Mumbai)
- ✅ Weather for Mumbai displayed
- ✅ Intent correctly classified as WEATHER

#### Test 2.3: Multiple Follow-ups
**Steps:**
1. `Places to visit in Rome`
2. `Suggest some more`
3. `Show me other attractions`

**Expected:**
- ✅ All three queries use Rome from STATE
- ✅ Each response shows different places (no duplicates)
- ✅ STATE tracks all shown_places across requests
- ✅ Up to 50 places can be cached and distributed

---

### 3. Location Switching (State Updates)

#### Test 3.1: Switching Cities
**Steps:**
1. First query: `Weather in Paris`
2. Second query: `Weather in Mumbai`
3. Third query: `What's the weather there?`

**Expected:**
- ✅ First query: STATE = {location: "Paris"}
- ✅ Second query: STATE = {location: "Mumbai"} (updated!)
- ✅ Third query: Uses Mumbai from STATE (NOT Paris)
- ✅ No confusion between cities

#### Test 3.2: Context After City Switch
**Steps:**
1. `Places in Paris`
2. `Places in Tokyo`
3. `Suggest some more`

**Expected:**
- ✅ First: STATE = {location: "Paris", shown_places: [Paris places]}
- ✅ Second: STATE = {location: "Tokyo", shown_places: []} (reset!)
- ✅ Third: More Tokyo places (uses last mentioned location from STATE)

---

### 4. State Persistence Tests

#### Test 4.1: State Survives Multiple Requests
**Steps:**
1. `Weather in Berlin`
2. Wait 30 seconds
3. `Suggest places`
4. Wait 1 minute
5. `What's the weather like?`

**Expected:**
- ✅ All queries use Berlin from STATE
- ✅ STATE persists in MongoDB between requests
- ✅ No re-extraction needed after first query

#### Test 4.2: State Isolation Between Sessions
**Steps:**
1. Open frontend in Browser 1
2. Query: `Places in Paris`
3. Open frontend in Browser 2 (new session)
4. Query: `Places in London`
5. In Browser 1: `Suggest some more`

**Expected:**
- ✅ Browser 1: More Paris places (STATE isolated by session_id)
- ✅ Browser 2: London places (different session_id)
- ✅ No cross-contamination between sessions

---

### 5. Natural Language Processing

#### Test 5.1: Conversational Weather Query
**Input:** `I'm thinking of going to Barcelona this weekend, how's the weather?`

**Expected:**
- ✅ Location extracted: Barcelona
- ✅ Intent: WEATHER
- ✅ Weather data returned
- ✅ STATE updated: `current_location = "Barcelona"`

#### Test 5.2: Complex Trip Planning
**Input:** `I want to explore New York City, what should I know?`

**Expected:**
- ✅ Location extracted: New York City
- ✅ Intent: BOTH
- ✅ Weather + Places returned
- ✅ STATE updated with NYC location and places

---

### 6. Caching Behavior

#### Test 6.1: Weather Cache
**Steps:**
1. Query: `Weather in London`
2. Wait 5 seconds
3. Query: `Weather in London` again

**Expected:**
- ✅ First query: "Weather cache MISS" in backend logs, API called
- ✅ Second query: "Weather cache HIT" in backend logs, instant response
- ✅ Cache valid for 1 hour

#### Test 6.2: Places Cache
**Steps:**
1. Query: `Places in Berlin`
2. Query: `Places in Berlin` (immediate)

**Expected:**
- ✅ First query: "Places cache MISS", Overpass API + LLM called
- ✅ Second query: "Places cache HIT", instant response
- ✅ Cache stores up to 50 places for 1 hour

---

### 7. Hybrid Places System

#### Test 7.1: Major City
**Input:** `Places to visit in Paris`

**Expected:**
- ✅ Backend logs show: "Getting LLM suggestions for Paris"
- ✅ Backend logs show: "Total places: X (Overpass: Y, LLM: Z)"
- ✅ Mix of nearby attractions (Overpass) + famous landmarks (LLM)
- ✅ Response time < 10 seconds

#### Test 7.2: Small City
**Input:** `Places to visit in [small city]`

**Expected:**
- ✅ Overpass may return fewer results
- ✅ LLM fills in with popular attractions
- ✅ Combined list still provides good suggestions

---

### 8. Error Handling

#### Test 8.1: Invalid Location
**Input:** `Weather in Xyzabc123`

**Expected:**
- ✅ Error message: "I'm sorry, I couldn't find a location matching 'Xyzabc123'"
- ✅ Intent: UNKNOWN
- ✅ No crash, graceful error handling
- ✅ STATE not updated with invalid location

#### Test 8.2: No Location in State
**Steps:**
1. New session (no history)
2. Query: `What's the weather there?`

**Expected:**
- ✅ System attempts extraction, returns None
- ✅ Checks STATE, finds no current_location
- ✅ Returns error: "I need to know which location you're interested in"
- ✅ No crash

#### Test 8.3: Empty Message
**Input:** `` (empty)

**Expected:**
- ✅ Frontend validation or backend handles gracefully

---

### 9. UI Features

#### Test 9.1: Debug Mode
**Steps:**
1. Enable "Show Debug Info" in sidebar
2. Make any query

**Expected:**
- ✅ Debug section shows:
  - Extracted location
  - Intent classification
  - Agent steps
  - Raw data (weather/places)
  - **Session state info** (current_location, shown_places count)

#### Test 9.2: Backend Status
**Expected:**
- ✅ Sidebar shows "Backend Status: ✅ Connected" when healthy
- ✅ Shows "❌ Disconnected" if backend down

#### Test 9.3: Example Queries
**Expected:**
- ✅ Sidebar shows 4-5 example queries
- ✅ Clicking an example populates the input field

---

### 10. Performance

#### Test 10.1: Response Time - Weather
**Input:** `Weather in any city`

**Expected:**
- ✅ Response within 5 seconds (first time)
- ✅ Response within 1 second (cached)
- ✅ STATE update adds < 100ms overhead

#### Test 10.2: Response Time - Places
**Input:** `Places in any city`

**Expected:**
- ✅ Response within 10 seconds (first time)
- ✅ Overpass query completes in 3-5 seconds
- ✅ LLM suggestions add 2-4 seconds
- ✅ Response within 1 second (cached)
- ✅ STATE operations add minimal overhead

#### Test 10.3: Timeout Handling
**Steps:**
1. Make a complex query
2. If timeout occurs (45 seconds)

**Expected:**
- ✅ Error message displayed
- ✅ No crash
- ✅ Can make new queries

---

## 🔌 API Testing

### Backend Health Check
```bash
curl http://localhost:8000/health
```
**Expected:** `{"status": "healthy"}`

### Chat Endpoint Test
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "Weather in Paris"
  }'
```

**Expected:** JSON response with weather data

### State Verification
```bash
# After the above query, check state was created
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "What is the weather there?"
  }'
```

**Expected:** Weather for Paris (from STATE, not new extraction)

---

## 💾 Database Testing

### MongoDB Connection
```bash
# If using Docker
docker exec -it travel_agent_mongodb mongosh

# If local MongoDB
mongosh
```

### State Collection Queries
```javascript
// List databases
show dbs

// Use travel agent database
use travel_agent_db

// Check collections
show collections
// Expected: chats, weather_cache, places_cache, conversation_states

// View conversation states
db.conversation_states.find().pretty()

// Check specific session state
db.conversation_states.findOne({session_id: "test-session"})

// Expected output:
{
  "_id": ObjectId("..."),
  "session_id": "test-session",
  "current_location": "Paris",
  "current_lat": 48.8566,
  "current_lon": 2.3522,
  "shown_places": ["Eiffel Tower", "Louvre", ...],
  "updated_at": ISODate("...")
}

// Count states
db.conversation_states.countDocuments()

// View recent chats
db.chats.find().sort({timestamp: -1}).limit(5)

// Check weather cache
db.weather_cache.find().limit(5)

// Check places cache
db.places_cache.find().limit(5)

// Clear a session's state (testing)
db.conversation_states.deleteOne({session_id: "test-session"})

// Clear all states (reset testing)
db.conversation_states.deleteMany({})
```

### State Update Verification
```javascript
// Before query
db.conversation_states.findOne({session_id: "test-123"})
// Expected: null or old state

// After "Weather in Tokyo" query
db.conversation_states.findOne({session_id: "test-123"})
// Expected: {current_location: "Tokyo", current_lat: ..., current_lon: ...}

// After "Suggest places" follow-up
db.conversation_states.findOne({session_id: "test-123"})
// Expected: shown_places array now has 8 items
```

---

## 🐳 Docker Testing

### Container Health
```bash
# Check all containers are running
docker-compose ps

# Expected: mongodb, backend, frontend all "Up"
```

### Container Logs
```bash
# View backend logs (look for state operations)
docker-compose logs -f backend
# Look for: "Loaded session state", "State updated"

# View frontend logs
docker-compose logs -f frontend

# View MongoDB logs (reduce verbosity)
docker-compose logs mongodb | tail -20
```

### Network Testing
```bash
# Test backend from frontend container
docker exec travel_agent_frontend curl http://backend:8000/health

# Expected: {"status": "healthy"}
```

### State Persistence Test
```bash
# 1. Start containers
docker-compose up -d

# 2. Make a query (creates state)
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "persist-test", "message": "Weather in Paris"}'

# 3. Restart backend only
docker-compose restart backend

# 4. Make follow-up query
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"session_id": "persist-test", "message": "What about places?"}'

# Expected: Still uses Paris from STATE (persisted in MongoDB)
```

---

## 📊 Load Testing (Optional)

### Test Multiple Concurrent Requests
```bash
# Install Apache Bench (if not installed)
# brew install httpd (macOS)

# Create payload
cat > payload.json << EOF
{
  "session_id": "load-test",
  "message": "Weather in Paris"
}
EOF

# Run load test
ab -n 100 -c 10 -p payload.json -T application/json http://localhost:8000/chat
```

### State Concurrency Test
```bash
# Test state updates under concurrent load
for i in {1..10}; do
  curl -X POST http://localhost:8000/chat \
    -H "Content-Type: application/json" \
    -d "{\"session_id\": \"concurrent-$i\", \"message\": \"Weather in City-$i\"}" &
done

# Verify all states created
mongosh travel_agent_db --eval "db.conversation_states.countDocuments()"
# Expected: 10 documents
```

---

## 🎯 Key Testing Scenarios

### Scenario 1: State-Based Context
```
Test: "Weather in Paris" → "Suggest places" → "Weather there?"
Verify: All use Paris from STATE, no LLM context confusion
```

### Scenario 2: State Updates
```
Test: "Weather in Paris" → "Weather in Tokyo" → "Suggest places"
Verify: Tokyo used (STATE updated), not Paris
```

### Scenario 3: State Persistence
```
Test: Query → Restart backend → Follow-up query
Verify: STATE survives restart (MongoDB persistence)
```

### Scenario 4: Place Tracking
```
Test: "Places in Rome" (3x times)
Verify: Different places each time, no duplicates (STATE tracks shown_places)
```

---

## ✅ Success Criteria

### Test Passed When:
- ✅ All basic queries return correct data
- ✅ Follow-up questions use STATE correctly (not LLM context)
- ✅ City switching updates STATE properly
- ✅ STATE persists in MongoDB across requests
- ✅ No duplicate places in follow-up requests
- ✅ Cache works (instant responses on repeat queries)
- ✅ No crashes or 500 errors
- ✅ UI remains responsive
- ✅ Debug info shows correct STATE operations

### Test Failed When:
- ❌ Wrong location used (STATE not read/updated)
- ❌ STATE fallback fails (no current_location in STATE)
- ❌ Same places suggested repeatedly (shown_places not tracked)
- ❌ Context confusion between cities (STATE not updated)
- ❌ STATE lost after restart (MongoDB persistence issue)
- ❌ Timeout errors frequently
- ❌ 500 Internal Server Error
- ❌ UI freezes or crashes
- ❌ Backend container stops unexpectedly

---

## 🐛 Known Issues & Limitations

### Current Limitations:
1. **LLM Extraction** - Extraction quality depends on LLM provider
2. **Cache TTL** - 1 hour cache means data may be stale
3. **LLM Rate Limits** - Provider APIs have rate limits
4. **Overpass Timeout** - Complex queries may timeout in 15-20 seconds
5. **State Size** - shown_places limited to reasonable memory (currently ~50 places)

### Bug Reporting:
When reporting bugs, include:
- Input query
- Expected vs actual behavior
- Session ID (from UI)
- Backend logs (especially STATE operations)
- MongoDB state document
- Screenshots (if UI issue)

---

## 📝 Summary

**Key Takeaways:**
- **State = Single Source of Truth** stored in MongoDB
- **LLM = Tool for extraction, NOT context understanding**
- **Deterministic = No hallucination, reliable behavior**
- **Persistent = State survives restarts and multiple requests**
- **Testable = Easy to verify state updates in MongoDB**

This architecture eliminates LLM context confusion and provides a reliable, testable, and maintainable solution for conversation state management.
