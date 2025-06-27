import os
import re
import yaml
from datetime import datetime
from openai import OpenAI

# === CONFIG ===
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Word count threshold to flag thin content
MIN_WORD_COUNT = 600

# === UTILS ===
def extract_frontmatter(content):
    match = re.match(r"(?s)^---\n(.*?)\n---\n(.*)$", content)
    if match:
        frontmatter = yaml.safe_load(match.group(1))
        body = match.group(2)
        return frontmatter, body
    return {}, content

def dump_yaml_preserve_quotes(data):
    class QuotedDumper(yaml.SafeDumper):
        pass

    def quoted_presenter(dumper, value):
        if isinstance(value, str):
            return dumper.represent_scalar('tag:yaml.org,2002:str', value, style='"')
        return dumper.represent_scalar('tag:yaml.org,2002:str', value)

    QuotedDumper.add_representer(str, quoted_presenter)
    return yaml.dump(data, Dumper=QuotedDumper, sort_keys=False, allow_unicode=True)

def build_prompt(title, body):
    return f"""
You are **Casey Wren** — a calm, strategic productivity writer who specializes in long-form, SEO-optimized blog content. You write for **TickJoy**, a friendly productivity blog focused on helping creatives and knowledge workers regain clarity, focus, and joy in their routines.

Write a comprehensive blog post of **at least 1,000 words** in **Markdown format** about the topic: **\"{title}\"**

---

### ✨ Tone and Style Requirements:
- Natural, strategic, and helpful — like a coach who’s been in the trenches
- Avoid hype or hustle culture — focus on sustainable momentum and clarity
- Structure for readability: headings, short paragraphs, lists, and bullets
- Use `---` horizontal rules sparingly to separate major **in-body** sections (never at the very beginning)
- Include emojis (⚡, 💡, ✅) only where they **enhance comprehension**, such as in bullets or callouts — never decorative
- Write with empathy and depth — especially for readers dealing with overwhelm or burnout

---

### 🔐 E-E-A-T Trust Layer (Always Included):
- Use **first-hand experience language**: "What helped me was…", "After testing this for 2 weeks…"
- Include **Pro Tips**, **Common Pitfalls**, or **Try This** style callouts to show practical expertise
- Reference tools, studies, or respected productivity authors (e.g. Cal Newport, James Clear) naturally
- Show the reader that this isn’t theory — it’s *field-tested clarity*

---

### ⚙️ Product Mentions:
Naturally mention **1–3 of the following tools or products**, weaving them into relevant sections of the article. At least one should appear near the end. They must feel like genuine, tested tools — not sales pitches.

{body}
"""

def call_openai(prompt):
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a precise and powerful editor."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )
    return response.choices[0].message.content.strip()

# === MAIN PROCESSING ===
log_entries = []
for filename in os.listdir("."):
    if filename.endswith(".md"):
        with open(filename, "r", encoding="utf-8") as f:
            raw = f.read()

        frontmatter, body = extract_frontmatter(raw)
        title = frontmatter.get("title", os.path.splitext(filename)[0].replace("-", " "))
        prompt = build_prompt(title, body)

        print(f"Rewriting: {filename}")
        new_body = call_openai(prompt)

        # Remove markdown code fences if present
        new_body = re.sub(r"^```(?:markdown)?\n(.*?)\n```$", r"\1", new_body.strip(), flags=re.DOTALL)

        # Remove top-level # Title line if it matches frontmatter title
        new_body = re.sub(rf"^# +{re.escape(title)}\n+", "", new_body)

        word_count = len(new_body.split())
        frontmatter["date"] = frontmatter.get("date") or datetime.now().strftime("%Y-%m-%d")
        new_content = f"---\n{dump_yaml_preserve_quotes(frontmatter)}---\n{new_body}"

        with open(filename, "w", encoding="utf-8") as f:
            f.write(new_content)

        log_entries.append({
            "file": filename,
            "word_count": word_count,
            "flagged": word_count < MIN_WORD_COUNT
        })

with open("rewrite_log_tickjoy.txt", "w") as log:
    for entry in log_entries:
        log.write(f"{entry['file']}: {entry['word_count']} words" + (" ⚠️ THIN" if entry['flagged'] else "") + "\n")

print("\n✅ Casey Wren has completed all rewrites. Check rewrite_log_tickjoy.txt for status.")
