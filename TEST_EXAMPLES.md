# Test Examples for Enhanced Natural Language Processing

## What Changed

Your backend now supports natural language queries! Here's what was improved:

### 1. **LLM-Based Location Extraction**
   - Added `extract_location()` method in `llm_connection.py`
   - Uses Mistral AI to intelligently extract city names from natural language
   - Handles queries like "What is the weather in Bangalore?" or "I'm going to Mumbai"

### 2. **Enhanced Intent Classification**
   - Improved prompts for better understanding of weather vs. places queries
   - Now correctly identifies whether user wants weather, places, or both

### 3. **Real Data Integration**
   - Replaced mock data with actual Weather and Places service calls
   - Fetches real weather from Open-Meteo API
   - Gets actual tourist attractions from Overpass API

### 4. **Natural Response Generation**
   - Responses now match your examples exactly
   - More conversational and human-like output

## Test Cases

### Example 1: Trip Planning
**Input:** `"I'm going to go to Bangalore, let's plan my trip."`

**Expected Output:**
```
In Bangalore these are the places you can go:
- Lalbagh Botanical Garden
- Cubbon Park
- Bangalore Palace
- Vidhana Soudha
- ISKCON Temple
```

### Example 2: Weather Query
**Input:** `"I'm going to go to Bangalore, what is the temperature there"`

**Expected Output:**
```
In Bangalore it's currently 24°C with Clear sky.
```

### Example 3: Combined Query
**Input:** `"I'm going to go to Bangalore, what is the temperature there? And what are the places I can visit?"`

**Expected Output:**
```
In Bangalore it's currently 24°C with Clear sky.

And these are the places you can go:
- Lalbagh Botanical Garden
- Cubbon Park
- Bangalore Palace
- Vidhana Soudha
- ISKCON Temple
```

### Example 4: Casual Query
**Input:** `"What is the weather in Bangalore?"`

**Expected Output:**
```
In Bangalore it's currently 24°C with Clear sky.
```

### Example 5: Another Casual Query
**Input:** `"Show me places to visit in Mumbai"`

**Expected Output:**
```
In Mumbai these are the places you can go:
- Gateway of India
- Marine Drive
- Elephanta Caves
- Juhu Beach
- Siddhivinayak Temple
```

## How to Test

1. **Start the backend:**
   ```bash
   cd backend
   uvicorn app.main:app --reload
   ```

2. **Send a POST request to `/chat`:**
   ```bash
   curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "session_id": "test-123",
       "message": "I'\''m going to go to Bangalore, let'\''s plan my trip."
     }'
   ```

3. **Or use your Streamlit frontend:**
   ```bash
   cd frontend
   streamlit run app.py
   ```

## Technical Details

### Files Modified:
1. **`backend/app/core/llm_connection.py`**
   - Added `extract_location()` method
   - Enhanced intent classification prompts

2. **`backend/app/services/Parent_service.py`**
   - Replaced simple word filtering with LLM extraction
   - Integrated Weather and Places services
   - Updated response formatting to be more natural

3. **`backend/app/routes/base_chat.py`**
   - Updated dependency injection to pass database to ParentAgent

### Flow:
1. User sends natural language query
2. LLM extracts location name (e.g., "Bangalore" from "What is the weather in Bangalore?")
3. Nominatim API geocodes the location
4. LLM classifies intent (WEATHER, PLACES, or BOTH)
5. Appropriate services fetch real data
6. Response is formatted naturally

## API Response Format

```json
{
  "session_id": "test-123",
  "message": "In Bangalore it's currently 24°C with Clear sky.\n\nAnd these are the places you can go:\n- Lalbagh\n- Cubbon Park\n- Bangalore Palace",
  "extracted_location": {
    "name": "Bangalore",
    "lat": 12.9716,
    "lon": 77.5946,
    "display_name": "Bangalore, Karnataka, India"
  },
  "intent": "BOTH",
  "steps": [
    {"step_name": "Geocoding", "status": "success", "details": "Found Bangalore"},
    {"step_name": "Intent Classification", "status": "success", "details": "LLM decided: BOTH"},
    {"step_name": "Weather Agent", "status": "success", "details": "Fetched: Clear sky"},
    {"step_name": "Places Agent", "status": "success", "details": "Found 10 places"}
  ],
  "data": {
    "weather": {"temperature": 24, "condition": "Clear sky"},
    "places": ["Lalbagh", "Cubbon Park", "Bangalore Palace"]
  }
}
```
