import streamlit as st
import requests
from supabase import create_client, Client

st.set_page_config(
    page_title="Budget Healthy Meals",
    page_icon="🥗",
    layout="wide"
)

# Initialize session state for credentials
if 'credentials_set' not in st.session_state:
    st.session_state.credentials_set = False
if 'supabase' not in st.session_state:
    st.session_state.supabase = None

# Credentials Input Section
if not st.session_state.credentials_set:
    st.title("🔑 Setup Credentials")
    st.write("Enter your API credentials to get started")
    
    with st.form("credentials_form"):
        supabase_url = st.text_input("Supabase URL", placeholder="https://selnutqegiwghipwludz.supabase.co")
        supabase_key = st.text_input("sb_publishable_EBev4S20lHJldLdNR-7LmQ_IZMsUzEr", type="password")
        spoonacular_key = st.text_input("3bf816f6a7a447f18c4f86ba5f56506f", type="password")
        
        submitted = st.form_submit_button("Connect", type="primary")
        
        if submitted:
            if supabase_url and supabase_key and spoonacular_key:
                try:
                    # Test Supabase connection
                    supabase = create_client(supabase_url, supabase_key)
                    # Test query
                    supabase.table("users").select("email").limit(1).execute()
                    
                    # Store in session state
                    st.session_state.supabase = supabase
                    st.session_state.spoonacular_key = spoonacular_key
                    st.session_state.credentials_set = True
                    st.success("✅ Connected successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Connection failed: {str(e)}")
                    st.info("Make sure your Supabase tables are created (see SQL below)")
            else:
                st.warning("Please fill in all credentials")
    
    st.stop()

# Main App
supabase = st.session_state.supabase
SPOONACULAR_API_KEY = st.session_state.spoonacular_key

st.title("🥗 Budget-Friendly Healthy Meals")
st.write("Find delicious, healthy recipes that fit your budget!")

# Add a settings button to reset credentials
if st.sidebar.button("⚙️ Reset Credentials"):
    st.session_state.credentials_set = False
    st.session_state.supabase = None
    st.rerun()

# Sidebar for user information
with st.sidebar:
    st.header("Your Profile")
    
    email = st.text_input("Email", placeholder="your@email.com")
    zip_code = st.text_input("Zip Code", placeholder="12345", max_chars=5)
    budget = st.number_input("Weekly Budget ($)", min_value=10, max_value=500, value=50, step=5)
    
    if st.button("Save Profile", type="primary"):
        if email and zip_code and budget:
            try:
                # Upsert user in Supabase
                data = {
                    "email": email,
                    "zip_code": zip_code,
                    "budget": budget
                }
                response = supabase.table("users").upsert(data).execute()
                st.success("✅ Profile saved!")
                st.session_state.user_email = email
                st.session_state.user_budget = budget
            except Exception as e:
                st.error(f"❌ Error saving profile: {str(e)}")
        else:
            st.warning("Please fill in all fields")
    
    st.divider()
    st.caption("💡 Tip: Lower budgets show simpler, ingredient-efficient recipes")

# Main content area
tab1, tab2 = st.tabs(["Find Recipes", "Saved Recipes"])

with tab1:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        max_calories = st.slider("Max Calories per Serving", 100, 1000, 500, 50)
    
    with col2:
        cuisine = st.selectbox(
            "Cuisine Type",
            ["Any", "American", "Asian", "European", "Mexican", "Mediterranean", "Italian"]
        )
    
    with col3:
        diet = st.selectbox(
            "Diet Type",
            ["None", "Vegetarian", "Vegan", "Gluten Free", "Ketogenic"]
        )
    
    if st.button("Search Recipes", type="primary"):
        with st.spinner("Finding recipes..."):
            # Build API request
            params = {
                "apiKey": SPOONACULAR_API_KEY,
                "number": 9,
                "maxCalories": max_calories,
                "addRecipeInformation": True,
                "fillIngredients": True,
                "sort": "price"
            }
            
            if cuisine != "Any":
                params["cuisine"] = cuisine.lower()
            
            if diet != "None":
                params["diet"] = diet.lower().replace(" ", "")
            
            try:
                response = requests.get(
                    "https://api.spoonacular.com/recipes/complexSearch",
                    params=params
                )
                
                if response.status_code == 200:
                    recipes = response.json().get("results", [])
                    
                    if recipes:
                        st.success(f"✅ Found {len(recipes)} recipes!")
                        
                        # Display recipes in grid
                        cols = st.columns(3)
                        for idx, recipe in enumerate(recipes):
                            with cols[idx % 3]:
                                st.image(recipe.get("image", ""), use_container_width=True)
                                st.subheader(recipe["title"])
                                
                                # Recipe details
                                st.write(f"⏱️ Ready in: {recipe.get('readyInMinutes', 'N/A')} min")
                                st.write(f"🍽️ Servings: {recipe.get('servings', 'N/A')}")
                                
                                if "pricePerServing" in recipe:
                                    price = recipe["pricePerServing"] / 100
                                    st.write(f"💰 ${price:.2f} per serving")
                                
                                # Get recipe details button
                                if st.button(f"View Recipe", key=f"view_{recipe['id']}"):
                                    st.session_state.selected_recipe = recipe['id']
                                
                                # Save recipe button
                                if st.button(f"💾 Save", key=f"save_{recipe['id']}"):
                                    if hasattr(st.session_state, 'user_email'):
                                        try:
                                            save_data = {
                                                "user_email": st.session_state.user_email,
                                                "recipe_id": recipe['id'],
                                                "recipe_title": recipe['title'],
                                                "recipe_image": recipe.get('image', ''),
                                                "price_per_serving": recipe.get('pricePerServing', 0) / 100
                                            }
                                            supabase.table("saved_recipes").insert(save_data).execute()
                                            st.success("✅ Recipe saved!")
                                        except Exception as e:
                                            st.error(f"❌ Error: {str(e)}")
                                    else:
                                        st.warning("⚠️ Please save your profile first")
                                
                                st.divider()
                    else:
                        st.info("No recipes found. Try adjusting your filters.")
                else:
                    st.error(f"❌ API Error: {response.status_code}")
                    if response.status_code == 402:
                        st.warning("Daily API limit reached. Try again tomorrow or upgrade your API plan.")
            
            except Exception as e:
                st.error(f"❌ Error fetching recipes: {str(e)}")

with tab2:
    st.header("Your Saved Recipes")
    
    if hasattr(st.session_state, 'user_email'):
        try:
            response = supabase.table("saved_recipes")\
                .select("*")\
                .eq("user_email", st.session_state.user_email)\
                .order("created_at", desc=True)\
                .execute()
            
            saved_recipes = response.data
            
            if saved_recipes:
                st.success(f"📚 You have {len(saved_recipes)} saved recipes")
                
                cols = st.columns(3)
                for idx, recipe in enumerate(saved_recipes):
                    with cols[idx % 3]:
                        if recipe.get("recipe_image"):
                            st.image(recipe["recipe_image"], use_container_width=True)
                        st.subheader(recipe["recipe_title"])
                        st.write(f"💰 ${recipe.get('price_per_serving', 0):.2f} per serving")
                        st.caption(f"Saved: {recipe.get('created_at', '')[:10]}")
                        
                        if st.button(f"🗑️ Remove", key=f"remove_{recipe['id']}"):
                            supabase.table("saved_recipes").delete().eq("id", recipe['id']).execute()
                            st.rerun()
                        
                        st.divider()
            else:
                st.info("📭 No saved recipes yet. Start searching to save your favorites!")
        
        except Exception as e:
            st.error(f"❌ Error loading saved recipes: {str(e)}")
    else:
        st.info("⚠️ Please save your profile to view saved recipes.")

# Display selected recipe details
if hasattr(st.session_state, 'selected_recipe'):
    with st.expander("📖 Recipe Details", expanded=True):
        try:
            recipe_response = requests.get(
                f"https://api.spoonacular.com/recipes/{st.session_state.selected_recipe}/information",
                params={"apiKey": SPOONACULAR_API_KEY}
            )
            
            if recipe_response.status_code == 200:
                recipe_detail = recipe_response.json()
                
                col1, col2 = st.columns([1, 1])
                
                with col1:
                    st.image(recipe_detail.get("image", ""))
                
                with col2:
                    st.subheader(recipe_detail["title"])
                    summary = recipe_detail.get("summary", "").replace("<b>", "**").replace("</b>", "**")
                    # Remove HTML tags
                    import re
                    summary = re.sub('<[^<]+?>', '', summary)
                    st.write(summary)
                
                st.subheader("🥘 Ingredients")
                for ingredient in recipe_detail.get("extendedIngredients", []):
                    st.write(f"• {ingredient['original']}")
                
                st.subheader("👨‍🍳 Instructions")
                instructions = recipe_detail.get("instructions", "")
                if instructions:
                    # Remove HTML tags
                    import re
                    instructions = re.sub('<[^<]+?>', '', instructions)
                    st.write(instructions)
                else:
                    st.info("Instructions not available for this recipe")
                
                if st.button("❌ Close Details"):
                    del st.session_state.selected_recipe
                    st.rerun()
        
        except Exception as e:
            st.error(f"❌ Error loading recipe details: {str(e)}")

st.divider()
st.caption("Data powered by Spoonacular API | Built with Streamlit & Supabase")
