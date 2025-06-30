import streamlit as st
import uuid
import json
import os
from datetime import date
from collections import Counter
import pandas as pd
import matplotlib.pyplot as plt
from graphviz import Digraph
import openai
import pyaudio

from dotenv import load_dotenv

load_dotenv()

# Fetch the key
api_key = os.getenv("OPENAI_API_KEY")

# Optional: Print to check (only for debugging, not in production!)
# print("API Key:", api_key[:5] + "..." if api_key else "Not found")

MEMORY_FILE = "data/memories.json"
FAMILY_FILE = "data/family.json"
FOOD_LOG_FILE = "data/food_log.json"
FAMILY_PHOTO_DIR = "data\\family_photos".replace("\\", "/")

os.makedirs("data", exist_ok=True)
os.makedirs(FAMILY_PHOTO_DIR, exist_ok=True)
for f in [MEMORY_FILE, FAMILY_FILE, FOOD_LOG_FILE]:
    if not os.path.exists(f):
        with open(f, 'w') as fp:
            json.dump([], fp)

# Load/save/delete data
def load_data(filepath):
    with open(filepath, 'r') as f:
        return json.load(f)

def save_data(filepath, entry):
    data = load_data(filepath)
    data.append(entry)
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def update_data(filepath, updated):
    data = load_data(filepath)
    for i, item in enumerate(data):
        if item['id'] == updated['id']:
            data[i] = updated
            break
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

def delete_data(filepath, item_id):
    data = load_data(filepath)
    data = [item for item in data if item['id'] != item_id]
    with open(filepath, 'w') as f:
        json.dump(data, f, indent=4)

# Shortcuts
load_memories = lambda: load_data(MEMORY_FILE)
save_memory = lambda entry: save_data(MEMORY_FILE, entry)
update_memory = lambda updated: update_data(MEMORY_FILE, updated)
delete_memory = lambda item_id: delete_data(MEMORY_FILE, item_id)

load_family = lambda: load_data(FAMILY_FILE)
save_family = lambda entry: save_data(FAMILY_FILE, entry)
update_family = lambda updated: update_data(FAMILY_FILE, updated)
delete_family = lambda item_id: delete_data(FAMILY_FILE, item_id)

load_food_log = lambda: load_data(FOOD_LOG_FILE)
save_food_log = lambda entry: save_data(FOOD_LOG_FILE, entry)
update_food_log = lambda updated: update_data(FOOD_LOG_FILE, updated)
delete_food_log = lambda item_id: delete_data(FOOD_LOG_FILE, item_id)

# UI - Streamlit App
st.set_page_config(page_title="Memory AI", layout="centered")
st.title("🧠 Personal Memory Logger")
APP_PIN = os.getenv("APP_PIN", "1234")  # fallback default
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Enter PIN to Access App")
    pin_input = st.text_input("Enter PIN", type="password")
    if st.button("Unlock"):
        if pin_input == APP_PIN:
            st.session_state.authenticated = True
            st.success("Access granted!")
            st.rerun()
        else:
            st.error("Incorrect PIN")
    st.stop()  # 🚫 Stop app here if not authenticated
menu = st.sidebar.selectbox(
    "Menu",
    [
        "🎤 Speak a Memory",
        "Talk with me",
        "Add Memory",
        "View/Edit Memory",
        "Family Info",
        "Family Tree",
        "Life Insights",
        "About",
    ],
)
if menu == "Talk with me":
    st.header("🗣️ Talk to Your Past Self")
    memories = load_memories()
    family = load_family()
    id_name_details = {
    f['name']: {
        "relation": f.get('relation', 'Unknown'),
        "age": f.get('age', 'N/A'),
        "hobbies": ", ".join(f.get('hobbies', [])) or 'None'
    }
    for f in family
}
    
    # st.write(id_name_details)
    combined_text = "\n\n".join([
        f"Title: {m['title']}\nDate: {m['date']}\nDesc: {m['description']}\nEmotions: {', '.join(m['emotion'])}\nPeople Involved: {id_name_details}"
        for m in memories
    ]) if memories else ""
        
    openai.api_key = api_key
    user_prompt = st.text_area(
        "📝 Ask your past self something (e.g. 'What did I enjoy most as a child?')"
    )
    if st.button("Talk") and user_prompt:
        if not memories:
            st.info("No memories found. Please add some first.")
        else:
            try:
                response = openai.chat.completions.create(
                    model="gpt-4",
                    messages=[
                        {"role": "system", "content": "You are the user's digital memory. Respond as if you are their past self, drawing only from the memory log below. and dont say anything if you dont find the data, simply say did not find what you are looking for, dont tell that you are reading from a log, just be straightforward."},
                        {"role": "user", "content": f"Here are my memories:{combined_text}Question: {user_prompt}"}])
                st.markdown("### 💬 Response")
                st.write(response.choices[0].message.content)
            except Exception as e:
                st.error(f"Failed to get response: {e}")





if menu == "Life Insights":
    st.header("📊 Life Insights")
    st.write("Summarizing your memories for emotional and meaningful patterns...")
    memories = load_memories()
    if "openai_summary" not in st.session_state:
        st.session_state.openai_summary = None

    combined_text = "\n\n".join([
        f"Title: {m['title']}\nDate: {m['date']}\nDesc: {m['description']}\nEmotions: {', '.join(m['emotion'])}"
        for m in memories
    ]) if memories else ""
        
    openai.api_key = api_key
    try:
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                    {"role": "system", "content": "You are a helpful assistant summarizing personal life memories into deep emotional insights."},
                    {"role": "user", "content": f"Here are my life memories:{combined_text}Please summarize key emotional patterns, milestones, recurring people or themes."}
                ]
        )
        st.session_state.openai_summary = response.choices[0].message.content
    except Exception as e:
        st.error(f"Failed to fetch summary: {e}")

    if st.session_state.openai_summary:
        st.markdown("### 📝 Summary")
        st.write(st.session_state.openai_summary)
if menu == "Family Tree":
    st.header("🌳 Family Tree Viewer")
    family = load_family()
    g = Digraph()
    g.attr(rankdir='LR')

    id_map = {f['id']: f['name'] for f in family}
    for member in family:
        g.node(member['id'], label=f"{member['name']}\n({member['relation']})")
        for rel in member.get("relations", []):
            if isinstance(rel, dict) and 'to' in rel and 'type' in rel and rel['to'] in id_map:
                g.edge(member['id'], rel['to'], label=rel['type'])

    st.graphviz_chart(g)

    st.subheader("Add Relationship Between Members")
    names = {f['name']: f['id'] for f in family}
    person1 = st.selectbox("From", list(names.keys()), key="rel_from")
    person2 = st.selectbox("To (Related To)", [n for n in names.keys() if n != person1], key="rel_to")
    relation_type = st.selectbox("Relationship Type", ["parent", "child", "spouse", "sibling",])

    if st.button("Link Members"):
        data = load_family()
        for f in data:
            if f['id'] == names[person1]:
                if "relations" not in f:
                    f["relations"] = []
                new_relation = {"to": names[person2], "type": relation_type}
                if new_relation not in f["relations"]:
                    f["relations"].append(new_relation)
        with open(FAMILY_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        st.success(f"Linked {person1} → {person2} as {relation_type}")
        st.rerun()
if menu == "Add Memory":
    st.header("📥 Add a New Memory")
    title = st.text_input("Title")
    description = st.text_area("Description")
    memory_date = st.date_input("Date", value=date.today())
    emotion = st.multiselect("Emotion(s)", ["Happy", "Sad", "Excited", "Scared", "Angry", "Grateful"])
    tags = st.text_input("Tags (comma-separated)").split(',')
    family_data = load_family()
    family_names = [member['name'] for member in family_data]
    selected_people = st.multiselect("People Involved", family_names)
    location = st.text_input("Location")

    if st.button("Save Memory"):
        memory = {
            "id": str(uuid.uuid4()),
            "title": title,
            "description": description,
            "date": str(memory_date),
            "emotion": [e.strip() for e in emotion],
            "tags": [t.strip() for t in tags if t.strip()],
            "people": selected_people,
            "location": location
        }
        save_memory(memory)
        st.success("Memory saved successfully!")

elif menu == "View/Edit Memory":
    st.header("✏️ View or Edit Memories")
    memories = load_memories()
    memory_titles = [m['title'] for m in memories]
    selected_title = st.selectbox("Select a memory to edit", memory_titles)
    selected_memory = next((m for m in memories if m['title'] == selected_title), None)
    if selected_memory:
        title = st.text_input("Title", selected_memory['title'])
        description = st.text_area("Description", selected_memory['description'])
        memory_date = st.date_input("Date", value=date.fromisoformat(selected_memory['date']))
        emotion = st.multiselect("Emotion(s)", ["Happy", "Sad", "Excited", "Scared", "Angry", "Grateful"], default=selected_memory['emotion'])
        tags = st.text_input("Tags (comma-separated)", ", ".join(selected_memory['tags'])).split(',')
        family_data = load_family()
        family_names = [member['name'] for member in family_data]
        selected_people = st.multiselect("People Involved", family_names, default=selected_memory['people'])
        location = st.text_input("Location", selected_memory['location'])

        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Update Memory"):
                updated = {
                    "id": selected_memory['id'],
                    "title": title,
                    "description": description,
                    "date": str(memory_date),
                    "emotion": [e.strip() for e in emotion],
                    "tags": [t.strip() for t in tags if t.strip()],
                    "people": selected_people,
                    "location": location
                }
                update_memory(updated)
                st.success("Memory updated successfully!")
                st.rerun()
        with col2:
            if st.button("Delete Memory"):
                delete_memory(selected_memory['id'])
                st.success("Memory deleted!")
                st.rerun()

elif menu == "Family Info":
    st.header("👨‍👩‍👧‍👦 Add/Edit Family Members")
    family = load_family()
    member_names = [f['name'] for f in family]
    selected_member_name = st.selectbox("Select member to edit or add new", ["Add New"] + member_names)
    selected_member = next((f for f in family if f['name'] == selected_member_name), None) if selected_member_name != "Add New" else None
    name = st.text_input("Name", value=selected_member['name'] if selected_member else "")
    relation = st.selectbox("Relationship", ["Myself", "Parent", "Sibling", "Spouse", "Child", "Cousin", "Father","Mother","Bhabi","niece","nephew","Other"], index=["Myself", "Parent", "Sibling", "Spouse", "Child", "Cousin", "Father","Mother","Bhabi","niece","nephew","Other"].index(selected_member['relation']) if selected_member else 0)
    age = st.number_input("Age", min_value=0, max_value=120, step=1, value=selected_member['age'] if selected_member else 0)
    hobbies = st.text_input("Hobbies (comma-separated)", ", ".join(selected_member.get('hobbies', [])) if selected_member else "").split(',')
    photo = st.file_uploader("Upload Photo", type=["jpg", "jpeg", "png"])

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save Family Member"):
            photo_filename = selected_member['photo'] if selected_member and 'photo' in selected_member else ""
            if photo:
                photo_filename = os.path.join(FAMILY_PHOTO_DIR, f"{uuid.uuid4()}_{photo.name}")
                with open(photo_filename, "wb") as f:
                    f.write(photo.read())
            updated_member = {
                "id": selected_member['id'] if selected_member else str(uuid.uuid4()),
                "name": name,
                "relation": relation,
                "age": age,
                "hobbies": [h.strip() for h in hobbies if h.strip()],
                "photo": photo_filename
            }
            update_family(updated_member) if selected_member else save_family(updated_member)
            st.success("Family member saved!")
            st.rerun()
    with col2:
        if selected_member and st.button("Delete Family Member"):
            delete_family(selected_member['id'])
            st.success("Family member deleted!")
            st.rerun()

    st.subheader("📋 Family List (Visual Table)")
    if family:
        for f in family:
            with st.container():
                cols = st.columns([1, 2])
                with cols[0]:
                    if f.get("photo"):
                       safe_path = f["photo"].replace("\\", "/")
                       st.image(safe_path, width=100)
                with cols[1]:
                    st.markdown(f"**Name:** {f['name']}")
                    st.markdown(f"**Relation:** {f['relation']}")
                    st.markdown(f"**Age:** {f['age']}")
                    st.markdown(f"**Hobbies:** {', '.join(f.get('hobbies', []))}")
                st.markdown("---")
    else:
        st.info("No family members found. Add one above to begin.")
elif menu == "🎤 Speak a Memory":
    st.header("🎙️ Record a Memory with Your Voice")
    
    import speech_recognition as sr

    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    with mic as source:
        st.info("Adjusting for ambient noise... Please wait.")
        recognizer.adjust_for_ambient_noise(source)
        st.info("Speak now!")
        audio = recognizer.listen(source)
        st.success("Recording complete!")

    try:
        raw_text = recognizer.recognize_google(audio)
        st.markdown("**Transcribed Text:**")
        st.write(raw_text)

        # Categorize using GPT
        openai.api_key = api_key
        gpt_response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Categorize the user's memory. Return JSON with: title, emotions (list), tags (list), people (list of names if mentioned), and a short summary."},
                {"role": "user", "content": f"Memory: {raw_text}"}
            ]
        )

        memory_data = json.loads(gpt_response.choices[0].message.content)

        st.markdown("### 📌 Categorized Memory")
        st.json(memory_data)

        if st.button("Save This Memory"):
            memory = {
                "id": str(uuid.uuid4()),
                "title": memory_data.get("title", "Untitled"),
                "description": raw_text,
                "date": str(date.today()),
                "emotion": memory_data.get("emotions", []),
                "tags": memory_data.get("tags", []),
                "people": memory_data.get("people", []),
                "location": ""  # Optional: leave empty or infer from text
            }
            save_memory(memory)
            st.success("Memory saved successfully!")

    except sr.UnknownValueError:
        st.error("Sorry, could not understand the audio.")
    except Exception as e:
        st.error(f"Error: {e}")
elif menu == "Food Log":
    st.header("🍽️ Food Reaction Log")
    family = load_family()
    names = [f['name'] for f in family]

    logs = load_food_log()
    selected_log = st.selectbox("Select log to edit or choose 'New Log'", ["New Log"] + [f"{l['name']} - {l['food']} ({l['date']})" for l in logs])

    if selected_log == "New Log":
        selected_entry = None
    else:
        selected_entry = next((l for l in logs if f"{l['name']} - {l['food']} ({l['date']})" == selected_log), None)

    name = st.selectbox("Family Member", names, index=names.index(selected_entry['name']) if selected_entry else 0)
    food = st.text_input("Food Item", value=selected_entry['food'] if selected_entry else "")
    reaction = st.text_area("Reaction / Symptoms (if any)", value=selected_entry['reaction'] if selected_entry else "")
    meal_time = st.selectbox("Meal Time", ["Breakfast", "Lunch", "Dinner", "Snack"], index=["Breakfast", "Lunch", "Dinner", "Snack"].index(selected_entry['meal_time']) if selected_entry and 'meal_time' in selected_entry else 0)
    date_logged = st.date_input("Date", value=date.fromisoformat(selected_entry['date']) if selected_entry else date.today())

    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("Save Food Log"):
            log = {
                "id": selected_entry['id'] if selected_entry else str(uuid.uuid4()),
                "name": name,
                "food": food,
                "reaction": reaction,
                "meal_time": meal_time,
                "date": str(date_logged)
            }
            update_food_log(log) if selected_entry else save_food_log(log)
            st.success("Food log saved!")
            st.rerun()
    with col2:
        if selected_entry and st.button("Delete Food Log"):
            delete_food_log(selected_entry['id'])
            st.success("Food log deleted!")
            st.rerun()

    st.subheader("📒 Filter Logs")
    filter_name = st.selectbox("Filter by Member", ["All"] + names)
    logs = load_food_log()
    filtered_logs = [log for log in logs if filter_name == "All" or log['name'] == filter_name]

    for log in filtered_logs:
        st.write(f"👤 {log['name']} | 🍲 {log['food']} | 🕒 {log.get('meal_time', 'N/A')} | 📅 {log['date']} | 💬 Reaction: {log['reaction']}")
        st.markdown("---")

    st.subheader("📊 Common Allergens Chart")
    all_foods_with_reactions = [log['food'] for log in logs if log['reaction'].strip() != ""]
    if all_foods_with_reactions:
        food_counts = Counter(all_foods_with_reactions)
        food_df = pd.DataFrame(food_counts.items(), columns=["Food", "Count"])
        food_df = food_df.sort_values(by="Count", ascending=False)
        st.bar_chart(food_df.set_index("Food"))
    else:
        st.info("No allergic reactions logged yet.")

elif menu == "About":
    st.header("ℹ️ About This App")
    st.markdown("""
    **Memory AI** lets you log your daily or past experiences, emotions, and moments.
    You can also keep a record of your family members with their photos, hobbies, and food reactions.
    In future updates, you'll be able to **chat with your past self**, find patterns, and get life insights.✨

    Built with ❤️ using Streamlit and Python.
    """)
