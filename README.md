# PlateTrack_AI
SmartPlate AI is a multi-page app for personalized health and meal planning. It uses AI to identify groceries, generate 7-day meal plans, log meals from photos, track daily metrics, visualize trends, and provide guidance. Built with Streamlit and Google Gemini API, it simplifies healthy living.


Project Overview:
SmartPlate AI is an intelligent, multi-page web application designed to empower users in managing their health and nutrition through personalized meal planning, dietary tracking, and AI-driven guidance. It leverages advanced AI capabilities to transform raw grocery inputs into actionable meal plans and provides comprehensive tools for monitoring daily health metrics and visualizing progress.

Key Features:

Personalized Health Profile: Users can set and update their daily calorie goals, log health conditions (e.g., Type 2 Diabetes), specify dietary preferences (e.g., vegetarian, gluten-free), and indicate fasting types to tailor AI recommendations.

AI-Powered Weekly Meal Plan Generation:

Users upload images of their groceries or receipts.

The AI analyzes the image to identify edible food items.

Based on identified groceries and user's health profile, the AI iteratively generates a detailed 7-day meal plan, including dish names, estimated calories, ingredients, and step-by-step instructions for each meal (Breakfast, Lunch, Dinner, Snacks, Desserts as selected).

Meal Logging from Photos: Users can upload pictures of their meals, and the AI will estimate calorie counts and provide a description, automatically adding it to their daily health log.

Comprehensive Daily Health Tracking: Allows users to manually log daily calorie intake, blood sugar readings, exercise minutes, step counts, water consumption, and carbohydrate intake.

Data Visualization & Trends: Presents logged health data through interactive charts (e.g., daily calorie intake vs. goal, blood sugar trends, carbohydrate intake) to help users understand their progress over the last 7 days.

Personalized AI Guidance: Users can ask specific health and diet-related questions, and the AI provides concise, actionable, and encouraging advice based on their profile and logged data.

Intuitive Multi-Page Navigation: The application is structured into distinct pages (Health Profile, Meal Plan Generation, Meal Photo Log, Daily Tracking, Data Visualization, Progress & Guidance) with automatic navigation upon task completion, ensuring a streamlined user experience.

Technology Stack:

Frontend/Backend Framework: Streamlit (Python) for rapid web application development and interactive UI.

Artificial Intelligence: Google Gemini API (gemini-2.0-flash) for image analysis (grocery identification, meal calorie estimation) and natural language generation (meal plans, recipes, personalized guidance).

Data Handling: Pandas for data manipulation, Plotly Express for interactive data visualizations.

Image Processing: Base64 encoding for sending image data to the AI API.

Planned Data Persistence (Conceptual): Designed with considerations for Firebase (Firestore) integration for user profiles and daily logs, though current implementation focuses on session-based data for demonstration.

SmartPlate AI aims to simplify healthy living by bringing cutting-edge AI directly into daily dietary and fitness management.
