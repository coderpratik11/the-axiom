import csv
import os
import datetime
import re
import google.generativeai as genai
from datetime import date

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CSV_PATH = 'data/questions.csv'
POSTS_DIR = '_posts'

genai.configure(api_key=GEMINI_API_KEY)

def get_best_model():
    """
    Dynamically finds a working model available to the API key
    to avoid '404 Model Not Found' errors.
    """
    print("Searching for available Gemini models...")
    try:
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        print(f"Available models: {available_models}")

        # Priority list (Newest to Oldest)
        preferences = [
            'models/gemini-1.5-flash',
            'models/gemini-1.5-flash-001',
            'models/gemini-1.5-pro',
            'models/gemini-1.5-pro-001',
            'models/gemini-pro',
            'models/gemini-1.0-pro'
        ]

        for pref in preferences:
            if pref in available_models:
                print(f"✅ Selected Model: {pref}")
                return genai.GenerativeModel(pref)
        
        # Fallback: Pick the first one that says 'gemini'
        for m in available_models:
            if 'gemini' in m:
                print(f"⚠️ Fallback Model: {m}")
                return genai.GenerativeModel(m)

        raise Exception("No Gemini models found available for this key.")
        
    except Exception as e:
        print(f"Error listing models: {e}")
        # Ultimate fallback if list_models fails
        return genai.GenerativeModel('gemini-pro')

# Initialize the smart model
model = get_best_model()

def get_target_count():
    # Weekend = 8 posts, Weekday = 4 posts
    if datetime.datetime.today().weekday() >= 5:
        return 8
    return 4

def clean_filename(text):
    return re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().replace(' ', '-').lower()[:50]

def generate_blog_post(question_text):
    prompt = f"""
    Act as a Staff Engineer. Determine the technical TOPIC of this question (e.g., Networking, Database).
    Write a technical blog post for: "{question_text}"
    
    Structure strictly as Markdown:
    ---
    layout: post
    title: "Daily Learning: {question_text}"
    ---
    
    # The Question: {question_text}

    ## 1. Key Concepts
    (Explain simply)

    ## 2. Topic Tag
    **Topic:** #(Insert inferred topic)

    ## 3. Real World Story
    (A short case study)

    ## 4. Bottlenecks
    (What goes wrong)

    ## 5. Resolutions
    (How to fix it)

    ## 6. Technologies
    (Tools used)

    ## 7. Learn Next
    (Related topics)
    """
    response = model.generate_content(prompt)
    return response.text

def main():
    if not os.path.exists(POSTS_DIR):
        os.makedirs(POSTS_DIR)

    target_count = get_target_count()
    print(f"Today's Target: {target_count}")
    
    rows = []
    processed_count = 0
    
    if not os.path.exists(CSV_PATH):
        print("CSV not found!")
        return

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if 'Status' not in fieldnames: fieldnames.append('Status')
        rows = list(reader)

    for row in rows:
        if processed_count >= target_count: break
        if row.get('Status') == 'Published': continue
            
        print(f"Generating: {row['Question'][:30]}...")
        try:
            content = generate_blog_post(row['Question'])
            content = content.replace("```markdown", "").replace("```", "")
            
            filename = f"{date.today()}-{clean_filename(row['Question'])}.md"
            with open(os.path.join(POSTS_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(content)
                
            row['Status'] = 'Published'
            processed_count += 1
        except Exception as e:
            print(f"Error generating content: {e}")

    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Run Complete. Generated {processed_count} posts.")

if __name__ == "__main__":
    main()
