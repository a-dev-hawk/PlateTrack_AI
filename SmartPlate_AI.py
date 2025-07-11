import streamlit as st
import requests
import json
from datetime import date, timedelta
import base64 # Required for encoding images
import pandas as pd # For data manipulation for charts
import plotly.express as px # For interactive charts
import re # For regular expressions to extract JSON

# --- Configuration ---
# The API key is automatically provided by the Canvas environment if left as an empty string.
# For local development, you would replace this with your actual API key.
API_KEY = "AIzaSyBc0rnb7NbKjMsvByBLoj7CHU6sCgbRuJw"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

# --- Firebase Emulation/Initialization for Local Development ---
# In a real Canvas environment, these globals are provided.
# For local testing, you might need to mock them or provide dummy values.
try:
    firebase_config = json.loads(__firebase_config)
    app_id = __app_id
    initial_auth_token = __initial_auth_token
except NameError:
    # Fallback for local development outside Canvas
    st.warning("Running locally without Canvas environment variables. Firestore will not be fully functional.")
    firebase_config = {
        "apiKey": "YOUR_FIREBASE_API_KEY", # Replace with your actual Firebase API Key for local testing
        "authDomain": "YOUR_FIREBASE_AUTH_DOMAIN",
        "projectId": "YOUR_FIREBASE_PROJECT_ID",
        "storageBucket": "YOUR_FIREBASE_STORAGE_BUCKET",
        "messagingSenderId": "YOUR_FIREBASE_MESSAGING_SENDER_ID",
        "appId": "YOUR_FIREBASE_APP_ID"
    }
    app_id = "default-healthquest-app" # A default app ID for local testing
    initial_auth_token = None # No initial auth token for local anonymous sign-in

# Initialize Firebase (only if not already initialized)
if 'firebase_app' not in st.session_state:
    # For this example, we'll simulate client-side Firestore interaction
    # by focusing on the LLM calls and leaving Firestore interaction as conceptual for Python.
    # If the user explicitly asks for Python Firestore integration, we'd add firebase_admin setup.
    st.session_state.firebase_initialized = True
    st.session_state.db = "Firestore_Instance_Placeholder" # Placeholder
    st.session_state.auth = "Auth_Instance_Placeholder" # Placeholder
    st.session_state.user_id = "anonymous_user_id" # Placeholder for now
    st.session_state.is_auth_ready = True # Assume ready for demo


# --- Session State for App Data (MUST BE AT THE TOP FOR INITIALIZATION) ---
# Ensure these are initialized before any UI elements try to access them.
if 'user_profile' not in st.session_state:
    st.session_state.user_profile = {
        "calorie_goal": 2000,
        "health_conditions": "",
        "dietary_preferences": "",
        "fasting_type": "None", # New field for fasting
        "user_id_display": "N/A" # To display user ID
    }
if 'daily_logs' not in st.session_state:
    # Added 'carbs' to the daily_logs structure
    st.session_state.daily_logs = {} # { 'YYYY-MM-DD': { 'calories': X, 'sugar': Y, 'carbs': C, 'meal_plan': {...}, 'exercise': Z, 'steps': A, 'water': B, 'meals_logged_from_photo': [] } }
if 'generated_weekly_meal_plan' not in st.session_state: # New: Stores the last generated weekly plan
    st.session_state.generated_weekly_meal_plan = {} # { 'YYYY-MM-DD': { ...daily_meal_plan_data... } }
if 'identified_groceries' not in st.session_state:
    st.session_state.identified_groceries = ""
if 'points' not in st.session_state: # Ensure 'points' is initialized
    st.session_state.points = 0
if 'last_checkin_day' not in st.session_state: # Ensure 'last_checkin_day' is initialized
    st.session_state.last_checkin_day = None
if 'streak' not in st.session_state: # Ensure 'streak' is initialized
    st.session_state.streak = 0
if 'current_page' not in st.session_state:
    st.session_state.current_page = "Health Profile"


# --- Firestore Helpers (Conceptual for Python, actual implementation requires firebase_admin) ---
# These functions are placeholders for actual Firestore operations.
# For a full Python backend with Firestore, you'd use firebase_admin SDK.
def load_user_profile(user_id):
    st.session_state.user_profile["user_id_display"] = user_id # Update display ID
    st.session_state.is_auth_ready = True # Assume auth is ready after getting user_id
    # Simulate loading for demo
    if 'loaded_profile' not in st.session_state: # Load once per session for demo
        st.session_state.loaded_profile = True
        # For a real app, you'd fetch from Firestore here
        pass
    return st.session_state.user_profile # Return current session state for demo

def save_user_profile(user_id, profile_data):
    st.session_state.user_profile.update(profile_data) # Update session state for demo
    st.success("Profile saved!")

def load_daily_logs(user_id):
    return st.session_state.daily_logs # Return current session state for demo

def save_daily_log(user_id, log_date, log_data):
    st.session_state.daily_logs[log_date] = log_data # Update session state for demo
    st.success(f"Log for {log_date} saved!")

# --- Helper function to extract JSON from potentially malformed AI output ---
def extract_json_from_string(text):
    """
    Attempts to extract a JSON object from a string that might contain
    additional conversational text or markdown code blocks.
    """
    # Try to find a JSON code block first
    match = re.search(r'```json\s*(\{.*\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass # Fallback to direct parsing if code block is malformed

    # If no code block or malformed, try to find the first and last curly brace
    # and parse the content between them. This is more aggressive.
    brace_start = text.find('{')
    brace_end = text.rfind('}')
    if brace_start != -1 and brace_end != -1 and brace_end > brace_start:
        json_candidate = text[brace_start : brace_end + 1]
        try:
            return json.loads(json_candidate)
        except json.JSONDecodeError:
            pass
    
    # As a last resort, try parsing the whole string directly
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None # Could not extract valid JSON


# --- Page Functions ---

def show_profile_page():
    st.header("1. Your Health Profile 👤")
    st.markdown("Set up your personal health goals and preferences.")
    with st.expander("Set/Update Profile"):
        st.session_state.user_profile["calorie_goal"] = st.number_input(
            "Daily Calorie Goal (kcal):",
            min_value=500, max_value=5000, value=st.session_state.user_profile["calorie_goal"], step=100
        )
        st.session_state.user_profile["health_conditions"] = st.text_input(
            "Any health conditions? (e.g., 'Type 2 Diabetes', 'High Blood Pressure')",
            value=st.session_state.user_profile["health_conditions"],
            placeholder="e.g., 'Type 2 Diabetes'"
        )
        st.session_state.user_profile["dietary_preferences"] = st.text_input(
            "Any dietary preferences? (e.g., 'vegetarian', 'gluten-free', 'low-carb')",
            value=st.session_state.user_profile["dietary_preferences"],
            placeholder="e.g., 'vegan, no nuts'"
        )
        st.session_state.user_profile["fasting_type"] = st.selectbox(
            "Type of Fasting (for recommendations):",
            ["None", "Intermittent (e.g., 16:8)", "OMAD (One Meal A Day)", "24-hour fast (1-2 times/week)"],
            index=["None", "Intermittent (e.g., 16:8)", "OMAD (One Meal A Day)", "24-hour fast (1-2 times/week)"].index(st.session_state.user_profile["fasting_type"])
        )
        if st.button("Save Profile"):
            save_user_profile(st.session_state.user_id, st.session_state.user_profile)
            st.session_state.current_page = "Weekly Meal Plan Generation" # Auto-navigate
            st.rerun() 
    st.markdown("---")

def show_meal_plan_generation_page():
    st.header("2. Upload Groceries & Get Weekly Meal Plan 📸")
    st.markdown("""
        Upload a clear picture of your groceries or a grocery bill/receipt.
        SmartPlate AI will identify edible items and generate a **7-day meal plan** for you.
        **Note:** AI's ability to accurately identify *only edible items* from complex receipts may vary.
        For best results, focus on a clear view of the food items themselves.
    """)
    uploaded_file = st.file_uploader("Choose an image file:", type=["jpg", "jpeg", "png"], key="grocery_uploader")

    if uploaded_file:
        st.image(uploaded_file, caption="Your uploaded groceries/bill", use_column_width=True)

    st.subheader("Meal Specifications for Plan:")
    meal_types_to_plan = st.multiselect(
        "Select the meals you want to include in each daily plan:",
        ["Breakfast", "Lunch", "Dinner", "Snack 1", "Snack 2", "Dessert"],
        default=["Breakfast", "Lunch", "Dinner", "Snack 1"]
    )

    if st.button("Analyze Groceries & Generate Weekly Meal Plan!"):
        if uploaded_file is None:
            st.warning("Please upload an image of your groceries.")
        elif not st.session_state.user_profile["calorie_goal"] or not meal_types_to_plan:
            st.warning("Please set your daily calorie goal and select meal types.")
        else:
            image_bytes = uploaded_file.getvalue()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')

            # --- Step 1: Identify Edible Items from Image ---
            grocery_identification_prompt_parts = [
                {
                    "text": """
                    Analyze the provided image. Identify and list all edible food items you can clearly see.
                    Ignore non-food items, prices, store names, or any other non-edible text/objects.
                    List the edible items as a comma-separated string.
                    Example: "apples, bananas, chicken breast, broccoli, milk, eggs"
                    """
                },
                {
                    "inlineData": {
                        "mimeType": uploaded_file.type,
                        "data": base64_image
                    }
                }
            ]

            grocery_payload = {
                "contents": [{"role": "user", "parts": grocery_identification_prompt_parts}]
            }

            st.info("Analyzing image to identify edible groceries... This might take a moment.")
            with st.spinner("AI is scanning your pantry..."):
                try:
                    grocery_response = requests.post(
                        GEMINI_API_URL,
                        headers={'Content-Type': 'application/json'},
                        data=json.dumps(grocery_payload)
                    )
                    grocery_response.raise_for_status()
                    grocery_result = grocery_response.json()

                    if grocery_result.get("candidates") and grocery_result["candidates"][0].get("content") and \
                       grocery_result["candidates"][0]["content"].get("parts") and \
                       grocery_result["candidates"][0]["content"]["parts"][0].get("text"):
                        st.session_state.identified_groceries = grocery_result["candidates"][0]["content"]["parts"][0].get("text")
                        st.success(f"Identified Groceries: {st.session_state.identified_groceries}")
                    else:
                        st.warning("Could not identify groceries from the image. Please try a clearer picture or list them manually below.")
                        st.session_state.identified_groceries = "" # Clear previous if failed
                        st.stop() # Stop if groceries not identified
                except Exception as e:
                    st.error(f"Error identifying groceries from image: {e}")
                    st.session_state.identified_groceries = "" # Clear previous if failed
                    st.stop()

            # --- Step 2: Generate Weekly Meal Plan (Iterative Daily Calls) ---
            if st.session_state.identified_groceries:
                st.session_state.generated_weekly_meal_plan = {} # Reset weekly plan
                today_date = date.today()
                
                st.info("Generating your personalized **weekly** meal plan (day by day)... This might take a few moments.")
                raw_ai_response_placeholder = st.empty() # Placeholder for debugging output

                all_successful = True
                for i in range(7):
                    day = today_date + timedelta(days=i)
                    day_str = day.isoformat()

                    daily_meal_plan_prompt_text = f"""
                    You are an expert nutritionist and chef, specializing in creating personalized meal plans.
                    Generate a meal plan for **{day_str}** using the identified groceries.
                    Prioritize using the identified groceries and ensure the plan aligns with the user's profile.
                    ONLY return the JSON object, no conversational text before or after.

                    **User Profile:**
                    - Daily Calorie Goal: {st.session_state.user_profile["calorie_goal"]} kcal
                    - Health Conditions: {st.session_state.user_profile["health_conditions"] if st.session_state.user_profile["health_conditions"].strip() else 'None'}
                    - Dietary Preferences: {st.session_state.user_profile["dietary_preferences"] if st.session_state.user_profile["dietary_preferences"].strip() else 'None'}
                    - Fasting Type: {st.session_state.user_profile["fasting_type"]}
                    **Meals to Include for this Day:** {', '.join(meal_types_to_plan)}
                    **Identified Groceries available for the week:** {st.session_state.identified_groceries}

                    Return the output as a JSON object with the following structure:
                    {{
                      "date": "{day_str}",
                      "daily_total_calories": "Approximate total calories for this day (e.g., '1800 kcal')",
                      "meal_plan": [
                        {{
                          "meal_type": "Breakfast",
                          "dish_name": "Creative dish name",
                          "estimated_calories": "Approximate calories (e.g., '350 kcal')",
                          "ingredients": ["Ingredient 1", "Ingredient 2"],
                          "instructions": "Step-by-step cooking instructions."
                        }},
                        {{
                          "meal_type": "Lunch",
                          "dish_name": "Creative dish name",
                          "estimated_calories": "Approximate calories (e.g., '500 kcal')",
                          "ingredients": ["Ingredient 1", "Ingredient 2"],
                          "instructions": "Step-by-step cooking instructions."
                        }}
                        // ... include all selected meal types
                      ],
                      "daily_notes": "Any specific notes for this day's plan."
                    }}
                    Ensure all fields are populated.
                    """

                    daily_meal_plan_payload = {
                        "contents": [{"role": "user", "parts": [{"text": daily_meal_plan_prompt_text}]}],
                        "generationConfig": {
                            "responseMimeType": "application/json",
                            "maxOutputTokens": 1024 # Limit tokens for single day, adjust if recipes are too short
                        }
                    }

                    with st.spinner(f"Crafting meal plan for {day_str}..."):
                        try:
                            response = requests.post(
                                GEMINI_API_URL,
                                headers={'Content-Type': 'application/json'},
                                data=json.dumps(daily_meal_plan_payload)
                            )
                            response.raise_for_status()
                            result = response.json()

                            # Display raw AI response for debugging
                            with raw_ai_response_placeholder.expander(f"Raw AI Response for {day_str} (for debugging)"):
                                st.json(result)

                            # Robust parsing of AI response
                            json_string = None
                            if result.get("candidates") and isinstance(result["candidates"], list) and len(result["candidates"]) > 0:
                                candidate = result["candidates"][0]
                                if isinstance(candidate, dict) and candidate.get("content") and isinstance(candidate["content"], dict) and candidate["content"].get("parts") and isinstance(candidate["content"]["parts"], list) and len(candidate["content"]["parts"]) > 0:
                                    part = candidate["content"]["parts"][0]
                                    if isinstance(part, dict) and part.get("text"):
                                        json_string = part["text"]

                            if json_string:
                                daily_plan_data = extract_json_from_string(json_string)

                                if daily_plan_data and 'meal_plan' in daily_plan_data: # Check for 'meal_plan' key in daily response
                                    st.session_state.generated_weekly_meal_plan[day_str] = daily_plan_data
                                    # Save each day's plan to daily_logs for consistency with tracking
                                    st.session_state.daily_logs[day_str] = st.session_state.daily_logs.get(day_str, {})
                                    st.session_state.daily_logs[day_str]['meal_plan'] = daily_plan_data # Save the entire daily plan object
                                    save_daily_log(st.session_state.user_id, day_str, st.session_state.daily_logs[day_str])
                                    st.success(f"Meal plan generated for {day_str}!")
                                else:
                                    st.warning(f"Could not parse meal plan for {day_str}. Structure unexpected or 'meal_plan' key missing. Raw AI text: {json_string}")
                                    all_successful = False
                            else:
                                st.warning(f"Could not generate meal plan for {day_str}. AI response text part missing or malformed. Raw AI response: {result}")
                                all_successful = False
                        except json.JSONDecodeError as e:
                            st.error(f"Failed to decode JSON for {day_str}. Error: {e}. Raw response: {result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A')}. Please check the 'Raw AI Response (for debugging)' above.")
                            all_successful = False
                        except requests.exceptions.RequestException as e:
                            st.error(f"Network error for {day_str}: {e}")
                            all_successful = False
                        except Exception as e:
                            st.error(f"An unexpected error occurred for {day_str}: {e}. Raw response: {result}")
                            all_successful = False
                
                if all_successful:
                    st.success("Weekly Meal Plan Generation Complete! 🎉")
                    st.session_state.current_page = "Progress & AI Guidance" # Auto-navigate
                    st.rerun() 
                else:
                    st.error("Weekly Meal Plan Generation finished with some errors. Please check individual day logs and raw responses.")
            else:
                st.warning("No edible groceries were identified from the image to create a meal plan.")
    st.markdown("---")

def show_meal_photo_log_page():
    st.header("3. Log a Meal from Photo 📸")
    st.markdown("""
        Take a picture of your meal (e.g., a restaurant dish) and SmartPlate AI will
        estimate its calories and add it to your daily log.
        **Note:** Calorie estimations from photos are approximate.
    """)

    meal_photo_date = st.date_input("Date of this meal:", value=date.today(), key="meal_photo_date")
    uploaded_meal_photo = st.file_uploader("Upload a picture of your meal:", type=["jpg", "jpeg", "png"], key="meal_photo_uploader")

    if uploaded_meal_photo:
        st.image(uploaded_meal_photo, caption="Your meal photo", use_column_width=True)

    if st.button("Estimate Calories & Log Meal!"):
        if uploaded_meal_photo is None:
            st.warning("Please upload a meal photo.")
        else:
            meal_image_bytes = uploaded_meal_photo.getvalue()
            base64_meal_image = base64.b64encode(meal_image_bytes).decode('utf-8')

            meal_estimation_prompt_parts = [
                {
                    "text": """
                    Analyze the provided image of a meal. Identify the main food items and
                    provide a concise description of the meal and its approximate total calorie count.
                    Return the output as a JSON object with the following structure:
                    {
                      "meal_description": "Description of the meal items.",
                      "estimated_calories": "Approximate total calories (e.g., 500 kcal)"
                    }
                    """
                },
                {
                    "inlineData": {
                        "mimeType": uploaded_meal_photo.type,
                        "data": base64_meal_image
                    }
                }
            ]

            meal_estimation_payload = {
                "contents": [{"role": "user", "parts": meal_estimation_prompt_parts}],
                "generationConfig": {
                    "responseMimeType": "application/json",
                    "responseSchema": {
                        "type": "OBJECT",
                        "properties": {
                            "meal_description": { "type": "STRING" },
                            "estimated_calories": { "type": "STRING" }
                        },
                        "required": ["meal_description", "estimated_calories"]
                    }
                }
            }

            st.info("Analyzing your meal photo and estimating calories... This might take a moment.")
            with st.spinner("AI is calculating your meal's energy..."):
                try:
                    meal_response = requests.post(
                        GEMINI_API_URL,
                        headers={'Content-Type': 'application/json'},
                        data=json.dumps(meal_estimation_payload)
                    )
                    meal_response.raise_for_status()
                    meal_result = meal_response.json()

                    if meal_result.get("candidates") and meal_result["candidates"][0].get("content") and \
                       meal_result["candidates"][0]["content"].get("parts") and \
                       meal_result["candidates"][0]["content"]["parts"][0].get("text"):
                        json_string = meal_result["candidates"][0]["content"]["parts"][0].get("text")
                        estimated_meal_data = json.loads(json_string)

                        meal_desc = estimated_meal_data.get("meal_description", "N/A")
                        estimated_cal_str = estimated_meal_data.get("estimated_calories", "0 kcal")
                        # Extract numerical part from estimated_calories string (e.g., "500 kcal" -> 500)
                        try:
                            estimated_cal_value = int(''.join(filter(str.isdigit, estimated_cal_str)))
                        except ValueError:
                            estimated_cal_value = 0 # Default to 0 if parsing fails

                        st.success(f"Meal Analyzed! 🍽️")
                        st.write(f"**Description:** {meal_desc}")
                        st.write(f"**Estimated Calories:** {estimated_cal_str}")

                        # Add estimated calories to the daily log for the selected date
                        meal_photo_date_str = meal_photo_date.isoformat()
                        st.session_state.daily_logs[meal_photo_date_str] = st.session_state.daily_logs.get(meal_photo_date_str, {})
                        
                        # Ensure 'logged_calories' is initialized before adding to it
                        current_logged_calories = st.session_state.daily_logs[meal_photo_date_str].get('logged_calories', 0)
                        st.session_state.daily_logs[meal_photo_date_str]['logged_calories'] = current_logged_calories + estimated_cal_value
                        
                        # Store meal photo log details
                        if 'meals_logged_from_photo' not in st.session_state.daily_logs[meal_photo_date_str]:
                            st.session_state.daily_logs[meal_photo_date_str]['meals_logged_from_photo'] = []
                        st.session_state.daily_logs[meal_photo_date_str]['meals_logged_from_photo'].append({
                            "description": meal_desc,
                            "calories": estimated_cal_str,
                            "timestamp": str(st.session_state.get('current_time', 'N/A')) # Placeholder for actual timestamp
                        })

                        save_daily_log(st.session_state.user_id, meal_photo_date_str, st.session_state.daily_logs[meal_photo_date_str])
                        st.info(f"Estimated {estimated_cal_str} added to your log for {meal_photo_date_str}!")
                        st.session_state.current_page = "Daily Health Tracking" # Auto-navigate
                        st.rerun() 

                    else:
                        st.error("Could not estimate meal calories. The AI response was empty or malformed.")
                        st.json(meal_result)
                except json.JSONDecodeError as e:
                    st.error(f"Failed to decode JSON from AI response. Error: {e}. Raw response: {meal_result.get('candidates', [{}])[0].get('content', {}).get('parts', [{}])[0].get('text', 'N/A')}")
                except requests.exceptions.RequestException as e:
                    st.error(f"An error occurred while connecting to the AI service: {e}")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")
    st.markdown("---")

def show_daily_tracking_page():
    st.header("4. Daily Health Tracking �")
    st.markdown("Log your daily health metrics here.")
    today_track = st.date_input("Select Date to Track", value=date.today(), key="track_date")
    today_str_track = today_track.isoformat()

    current_day_log = st.session_state.daily_logs.get(today_str_track, {})
    logged_calories = current_day_log.get('logged_calories', None)
    logged_sugar = current_day_log.get('logged_sugar', None)
    logged_exercise = current_day_log.get('logged_exercise', None)
    logged_steps = current_day_log.get('logged_steps', None)
    logged_water = current_day_log.get('logged_water', None)
    logged_carbs = current_day_log.get('logged_carbs', None) # New: Carbs


    col1, col2 = st.columns(2)
    with col1:
        new_logged_calories = st.number_input(
            "Calories Consumed (kcal):",
            min_value=0, value=logged_calories if logged_calories is not None else 0, step=50,
            key=f"calories_{today_str_track}"
        )
    with col2:
        new_logged_sugar = st.number_input(
            "Blood Sugar Reading (mg/dL - if applicable):",
            min_value=0, value=logged_sugar if logged_sugar is not None else 0, step=1,
            key=f"sugar_{today_str_track}"
        )

    col3, col4, col5, col6 = st.columns(4) # Added a column for carbs
    with col3:
        new_logged_exercise = st.number_input(
            "Exercise (minutes):",
            min_value=0, value=logged_exercise if logged_exercise is not None else 0, step=10,
            key=f"exercise_{today_str_track}"
        )
    with col4:
        new_logged_steps = st.number_input(
            "Steps (count):",
            min_value=0, value=logged_steps if logged_steps is not None else 0, step=500,
            key=f"steps_{today_str_track}"
        )
    with col5:
        new_logged_water = st.number_input(
            "Water (liters):",
            min_value=0.0, value=logged_water if logged_water is not None else 0.0, step=0.5, format="%.1f",
            key=f"water_{today_str_track}"
        )
    with col6: # New: Carbs input
        new_logged_carbs = st.number_input(
            "Carbs Consumed (grams):",
            min_value=0, value=logged_carbs if logged_carbs is not None else 0, step=10,
            key=f"carbs_{today_str_track}"
        )


    if st.button(f"Log Data for {today_str_track}", key=f"log_data_button_{today_str_track}"): # Added key for uniqueness
        st.session_state.daily_logs[today_str_track] = st.session_state.daily_logs.get(today_str_track, {})
        st.session_state.daily_logs[today_str_track]['logged_calories'] = new_logged_calories
        st.session_state.daily_logs[today_str_track]['logged_sugar'] = new_logged_sugar
        st.session_state.daily_logs[today_str_track]['logged_exercise'] = new_logged_exercise
        st.session_state.daily_logs[today_str_track]['logged_steps'] = new_logged_steps
        st.session_state.daily_logs[today_str_track]['logged_water'] = new_logged_water
        st.session_state.daily_logs[today_str_track]['logged_carbs'] = new_logged_carbs # New: Save carbs
        save_daily_log(st.session_state.user_id, today_str_track, st.session_state.daily_logs[today_str_track])
        st.success(f"Health data logged for {today_str_track}!")
        st.session_state.current_page = "Data Visualization & Trends" # Auto-navigate
        st.rerun() 
    st.markdown("---")

def show_data_visualization_page():
    st.header("5. Data Visualization & Trends 📈")
    st.markdown("Visualize your health data over the last 7 days for better understanding.")

    # Prepare data for charting
    chart_data = []
    today_date = date.today()
    for i in range(7):
        day = today_date - timedelta(days=i)
        day_str = day.isoformat()
        log_data = st.session_state.daily_logs.get(day_str, {})
        chart_data.append({
            "Date": day_str,
            "Logged Calories": log_data.get('logged_calories', 0),
            "Calorie Goal": st.session_state.user_profile['calorie_goal'],
            "Logged Sugar": log_data.get('logged_sugar', None),
            "Logged Carbs": log_data.get('logged_carbs', 0)
        })

    # Reverse data to show oldest first on chart
    chart_df = pd.DataFrame(chart_data).sort_values(by="Date")

    if not chart_df.empty:
        st.subheader("Daily Calorie Intake vs. Goal")
        fig_calories = px.bar(
            chart_df,
            x="Date",
            y=["Logged Calories", "Calorie Goal"],
            barmode="group",
            title="Daily Calorie Intake vs. Goal",
            labels={"value": "Calories (kcal)", "variable": "Metric"},
            color_discrete_map={"Logged Calories": "#4CAF50", "Calorie Goal": "#FFC107"} # Green for logged, Amber for goal
        )
        st.plotly_chart(fig_calories, use_container_width=True)

        st.subheader("Daily Blood Sugar Readings")
        # Filter out None values for sugar chart
        sugar_df = chart_df.dropna(subset=['Logged Sugar'])
        if not sugar_df.empty:
            fig_sugar = px.line(
                sugar_df,
                x="Date",
                y="Logged Sugar",
                title="Daily Blood Sugar Readings",
                labels={"Logged Sugar": "Blood Sugar (mg/dL)"},
                markers=True,
                line_shape="linear",
                color_discrete_sequence=["#2196F3"] # Blue for sugar
            )
            st.plotly_chart(fig_sugar, use_container_width=True)
        else:
            st.info("No blood sugar data logged yet for charts.")

        st.subheader("Daily Carbohydrate Intake")
        fig_carbs = px.bar(
            chart_df,
            x="Date",
            y="Logged Carbs",
            title="Daily Carbohydrate Intake",
            labels={"Logged Carbs": "Carbohydrates (grams)"},
            color_discrete_sequence=["#9C27B0"] # Purple for carbs
        )
        st.plotly_chart(fig_carbs, use_container_width=True)

    else:
        st.info("Log some data in 'Daily Health Tracking' to see charts here!")
    st.markdown("---")

def show_progress_guidance_page():
    st.header("6. Your Progress & AI Guidance 📈")
    st.markdown("View your daily logs and get personalized insights.")

    # Display today's summary (already present, but re-emphasized here for context)
    st.subheader("Today's Summary:")
    today_summary_date_str = date.today().isoformat()
    today_log = st.session_state.daily_logs.get(today_summary_date_str, {})
    today_calories_logged = today_log.get('logged_calories', 0)
    today_sugar_logged = today_log.get('logged_sugar', 'N/A')
    today_exercise_logged = today_log.get('logged_exercise', 0)
    today_steps_logged = today_log.get('logged_steps', 0)
    today_water_logged = today_log.get('logged_water', 0.0)
    today_carbs_logged = today_log.get('logged_carbs', 0) # New
    calorie_goal = st.session_state.user_profile['calorie_goal']
    calories_left = calorie_goal - today_calories_logged

    st.markdown(f"**Calorie Budget:** {calorie_goal} kcal")
    st.markdown(f"**Calories Consumed Today:** {today_calories_logged} kcal")
    st.markdown(f"**Calories Left:** {calories_left} kcal")
    st.markdown(f"**Exercise Today:** {today_exercise_logged} minutes")
    st.markdown(f"**Steps Today:** {today_steps_logged} steps")
    st.markdown(f"**Water Today:** {today_water_logged} liters")
    st.markdown(f"**Carbs Today:** {today_carbs_logged} grams") # New
    if today_sugar_logged != 'N/A':
        st.markdown(f"**Blood Sugar Today:** {today_sugar_logged} mg/dL")

    # Display meals logged from photo
    if today_log.get('meals_logged_from_photo'):
        st.markdown("---")
        st.subheader("Meals Logged from Photo Today:")
        for meal_entry in today_log['meals_logged_from_photo']:
            st.write(f"- {meal_entry.get('description', 'N/A')} ({meal_entry.get('calories', 'N/A')})")

    st.markdown("---")

    # Weekly Meal Plan Overview (Next 7 Days with Expanders for Recipes)
    st.subheader("Weekly Meal Plan Overview (Next 7 Days):") # Updated title
    today_date = date.today()
    # Iterate for the next 7 days
    for i in range(7):
        day = today_date + timedelta(days=i) # Changed to next 7 days
        day_str = day.isoformat()
        
        # Check if a meal plan was generated for this specific day in the weekly plan
        day_plan_from_generated = st.session_state.generated_weekly_meal_plan.get(day_str)

        if day_plan_from_generated:
            with st.expander(f"📅 **{day_str}** - Meal Plan"):
                st.markdown(f"**Total Estimated Calories for Day:** {day_plan_from_generated.get('daily_total_calories', 'N/A')}")
                for meal in day_plan_from_generated.get('meal_plan', []):
                    st.markdown(f"---")
                    st.markdown(f"#### {meal.get('meal_type', 'Meal')}: {meal.get('dish_name', 'N/A')}")
                    st.markdown(f"**🔥 Estimated Calories:** {meal.get('estimated_calories', 'N/A')}")
                    st.markdown("**Ingredients:**")
                    for ingredient in meal.get('ingredients', []):
                        st.markdown(f"- {ingredient}")
                    st.markdown("**Instructions:**")
                    st.markdown(meal.get('instructions', 'N/A'))
                if day_plan_from_generated.get('daily_notes'):
                    st.markdown(f"---")
                    st.markdown(f"**Notes:** {day_plan_from_generated['daily_notes']}")
        else:
            st.info(f"📅 **{day_str}** - No meal plan generated for this day yet. Generate a weekly plan in Section 2!")


    st.markdown("---")
    st.subheader("Get Personalized Guidance")
    guidance_query = st.text_area(
        "Ask SmartPlate AI for advice:", # Updated title
        placeholder="e.g., 'How can I lower my sugar intake?', 'Tips for staying motivated with my diet.'"
    )

    if st.button("Get Guidance"):
        if guidance_query.strip():
            guidance_prompt = f"""
            You are a supportive and knowledgeable health coach.
            User's Profile:
            - Goal: {st.session_state.user_profile['calorie_goal']} kcal
            - Health Conditions: {st.session_state.user_profile['health_conditions'] if st.session_state.user_profile['health_conditions'].strip() else 'None'}
            - Dietary Preferences: {st.session_state.user_profile['dietary_preferences'] if st.session_state.user_profile['dietary_preferences'].strip() else 'None'}
            - Fasting Type: {st.session_state.user_profile['fasting_type']}
            User's recent activity (if available):
            - Calories Logged Today: {today_calories_logged}
            - Sugar Reading Today: {today_sugar_logged}
            - Exercise Today: {today_exercise_logged} minutes
            - Steps Today: {today_steps_logged} steps
            - Water Today: {today_water_logged} liters
            - Carbs Today: {today_carbs_logged} grams
            User's query: "{guidance_query.strip()}"

            Provide concise, actionable, and encouraging guidance (2-4 sentences) based on their profile, recent data, and query.
            """
            chat_history = [{"role": "user", "parts": [{"text": guidance_prompt}]}]
            payload = {"contents": chat_history}

            with st.spinner("Generating personalized guidance..."):
                try:
                    response = requests.post(
                        GEMINI_API_URL,
                        headers={'Content-Type': 'application/json'},
                        data=json.dumps(payload)
                    )
                    response.raise_for_status()
                    result = response.json()
                    if result.get("candidates") and result["candidates"][0].get("content") and \
                       result["candidates"][0]["content"].get("parts") and \
                       result["candidates"][0]["content"]["parts"][0].get("text"):
                        st.subheader("SmartPlate AI's Advice! 🌟") # Updated title
                        st.markdown(result["candidates"][0]["content"]["parts"][0]["text"])
                    else:
                        st.warning("Could not generate guidance.")
                except Exception as e:
                    st.error(f"Error getting guidance: {e}")
        else:
            st.warning("Please enter your query for guidance.")
    st.markdown("---")


# --- Main App Logic ---
st.sidebar.title("App Navigation")
page_options = [
    "Health Profile",
    "Weekly Meal Plan Generation",
    "Log Meal from Photo",
    "Daily Health Tracking",
    "Data Visualization & Trends",
    "Progress & AI Guidance"
]
st.session_state.current_page = st.sidebar.radio(
    "Go to",
    page_options,
    index=page_options.index(st.session_state.current_page) if st.session_state.current_page in page_options else 0
)

st.title("🍏 SmartPlate AI: Personalized Health & Meal Planner") # Main app title at the top
st.markdown("""
    Your AI companion for managing health, tracking intake, and getting personalized recipes!
    **Upload a picture of your groceries/bill**, set your goals, and let AI guide you.
""")

# Display the selected page content
if st.session_state.current_page == "Health Profile":
    show_profile_page()
elif st.session_state.current_page == "Weekly Meal Plan Generation":
    show_meal_plan_generation_page()
elif st.session_state.current_page == "Log Meal from Photo":
    show_meal_photo_log_page()
elif st.session_state.current_page == "Daily Health Tracking":
    show_daily_tracking_page()
elif st.session_state.current_page == "Data Visualization & Trends":
    show_data_visualization_page()
elif st.session_state.current_page == "Progress & AI Guidance":
    show_progress_guidance_page()

st.caption("Powered by Google Gemini AI")
