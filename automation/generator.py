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
    prompt = f"""
    You are a Principal Software Engineer writing a technical blog post. 
    The Topic is: "{question_text}"
    
    **DESIGN INSTRUCTIONS (Strictly Follow):**
    1. **Layout:** Use proper Markdown headers (##, ###) to structure the article.
    2. **Visuals:** Use tables for comparisons (e.g., Pros vs Cons).
    3. **Emphasis:** Use **bold** for key terms and `code blocks` for technical concepts.
    4. **Callouts:** Use blockquotes (>) for important "Pro Tips" or "Warnings".
    5. **Tone:** Professional, concise, and educational.

    **FRONT MATTER RULES:**
    - You MUST start with YAML Front Matter.
    - `toc: true` is MANDATORY.
    - `layout: post` is MANDATORY.
    - `categories` must be [System Design, <Subtopic>].
    - `tags` must be lowercase.

    **Output Structure:**
    ---
    title: "{question_text}"
    date: {date.today().strftime("%Y-%m-%d")}
    categories: [System Design, Concepts]
    tags: [interview, architecture, learning]
    toc: true
    layout: post
    ---
    
    ## 1. The Core Concept
    (Explain the concept simply using an analogy. Use a > blockquote for the definition.)

    ## 2. Deep Dive & Architecture
    (Technical details. Use `code snippets` or bullet points.)

    ## 3. Comparison / Trade-offs
    (MUST include a Markdown Table comparing options, e.g., TCP vs UDP or SQL vs NoSQL.)

    ## 4. Real-World Use Case
    (Where is this used? e.g., Netflix, Uber. Explain the "Why".)
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

    # Weekend = 8 posts, Weekday = 4 posts
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
        
        # Skip if already published
        if entry.get('Status') == 'Published': continue
            
        print(f"Processing: {entry['Question'][:30]}...")
        
        content = generate_blog_post(entry['Question'])
        
        if content:
            # Cleanup markdown wrapper if present
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
