import csv
import os
import datetime
import re
import google.generativeai as genai
from datetime import date

# --- CONFIGURATION ---
# This grabs the key from the secure vault
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
CSV_PATH = 'data/questions.csv'
POSTS_DIR = '_posts'

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_target_count():
    # 5 = Saturday, 6 = Sunday. 
    # Weekend: 4 daily + 4 extra = 8. Weekday: 4.
    if datetime.datetime.today().weekday() >= 5:
        return 8
    return 4

def clean_filename(text):
    # Removes special chars to make a safe filename
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
    # Ensure _posts directory exists
    if not os.path.exists(POSTS_DIR):
        os.makedirs(POSTS_DIR)

    target_count = get_target_count()
    print(f"Today's Target: {target_count}")
    
    rows = []
    processed_count = 0
    
    # Read CSV
    if not os.path.exists(CSV_PATH):
        print("CSV not found!")
        return

    with open(CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if 'Status' not in fieldnames: fieldnames.append('Status')
        rows = list(reader)

    # Process
    for row in rows:
        if processed_count >= target_count: break
        if row.get('Status') == 'Published': continue
            
        print(f"Generating: {row['Question'][:20]}...")
        try:
            content = generate_blog_post(row['Question'])
            # Clean up markdown code blocks if Gemini adds them
            content = content.replace("```markdown", "").replace("```", "")
            
            filename = f"{date.today()}-{clean_filename(row['Question'])}.md"
            with open(os.path.join(POSTS_DIR, filename), 'w', encoding='utf-8') as f:
                f.write(content)
                
            row['Status'] = 'Published'
            processed_count += 1
        except Exception as e:
            print(f"Error: {e}")

    # Save CSV
    with open(CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(rows)

if __name__ == "__main__":
    main()
