import json
import os
import re
import google.generativeai as genai
from datetime import date

# --- CONFIGURATION ---
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
JSON_PATH = 'data/questions.json'
POSTS_DIR = '_posts'

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def clean_filename(text):
    return re.sub(r'[^a-zA-Z0-9\s-]', '', text).strip().replace(' ', '-').lower()[:50]

def generate_blog_post(question_text):
    # We ask Gemini to generate the Front Matter explicitly for Chirpy
    prompt = f"""
    Act as a Staff Engineer. Write a technical blog post for: "{question_text}"
    
    **CRITICAL FORMATTING RULES:**
    1. You MUST start with YAML Front Matter.
    2. `categories` must be a list: [System Design, <Specific Subtopic>].
    3. `tags` must be lowercase: [<tag1>, <tag2>, <tag3>].
    
    Output format:
    ---
    title: "{question_text}"
    date: {date.today().strftime("%Y-%m-%d")}
    categories: [System Design, Deep Dive]
    tags: [architecture, learning]
    ---
    
    # 1. The Concept
    (Explain simply)

    # 2. Real World Analogy
    (Story time)

    # 3. Technical Deep Dive
    (Bottlenecks, Resolutions, Technologies)
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"Gemini Error: {e}")
        return None

def main():
    if not os.path.exists(POSTS_DIR):
        os.makedirs(POSTS_DIR)

    # Get Target Count (4 or 8)
    target_count = 8 if date.today().weekday() >= 5 else 4
    print(f"Target: {target_count}")
    
    if not os.path.exists(JSON_PATH):
        print("No JSON file found.")
        return

    with open(JSON_PATH, 'r', encoding='utf-8') as f:
        data = json.load(f)

    processed_count = 0

    for entry in data:
        if processed_count >= target_count: break
        if entry.get('Status') == 'Published': continue
            
        print(f"Processing: {entry['Question'][:30]}...")
        
        content = generate_blog_post(entry['Question'])
        
        if content:
            # Clean up if Gemini wrapped it in markdown quotes
            content = content.replace("```markdown", "").replace("```", "").strip()
            
            filename = f"{date.today()}-{clean_filename(entry['Question'])}.md"
            with open(os.path.join(POSTS_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(content)
                
            entry['Status'] = 'Published'
            processed_count += 1

    # Save JSON
    with open(JSON_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
    
    print(f"Done. Generated {processed_count} posts.")

if __name__ == "__main__":
    main()
