import openai
import streamlit as st
from datetime import datetime
import requests
import base64

# =========================
# 1) Set up credentials
# =========================
# We'll read these from Streamlit Secrets
# You must define these in your Streamlit "Secrets" settings:
#   OPENAI_API_KEY: your OpenAI key
#   GH_TOKEN: your GitHub personal access token
#   GH_OWNER: the GitHub username or org that owns the repo
#   GH_REPO: the name of the repo (public)
#
openai.api_key = st.secrets["OPENAI_API_KEY"]
GH_TOKEN = st.secrets["GH_TOKEN"]
GH_OWNER = st.secrets["GH_OWNER"]
GH_REPO = st.secrets["GH_REPO"]

# =========================
# 2) Intellectual Humility
# =========================
QUESTIONS = [
    "Can you describe a time you realized you were wrong about something important? How did you come to that realization, and what did you do afterward?",
    "What’s a topic you used to feel very certain about, but now feel less certain—or even uncertain—about? What made you reconsider?",
    "When you’re in a debate and you encounter evidence that contradicts your view, how do you usually respond?",
    "In areas you’re most knowledgeable about, do you ever worry that you might still have blind spots? How do you watch out for them?",
    "How do you decide which sources of information you trust and which you don’t?"
    # "I enjoy learning from people whose opinions differ from mine.",
    # "I find it easy to admit when I’m wrong.",
    # "I’m open to revisiting and potentially changing my core beliefs.",
    # "I often seek feedback and constructive criticism.",
    # "I quickly dismiss opposing viewpoints.",  # reverse scored
    # "I find it difficult to say 'I don’t know.'",  # reverse scored
    # "I value expertise in areas where I’m not knowledgeable.",
    # "I try to see issues from multiple perspectives.",
    # "It is important to me to be right, even if evidence suggests otherwise.",  # reverse scored
    # "I regularly reflect on how my beliefs may be biased or incomplete."
]
REVERSE_SCORED = []
# REVERSE_SCORED = [4, 5, 8]  # 0-based indices for Q5, Q6, Q9

def interpret_answer_with_chatgpt(question, user_answer):
    """
    Use the ChatCompletion API to interpret user's answer on a 1–5 scale
    where 1 = strongly indicates humility, 5 = strongly indicates lack of humility.
    """
    system_message = (
        "You are a helpful assistant. You will be given a question about intellectual humility "
        "and the user's answer. Your task: interpret how the user’s answer reflects "
        "their intellectual humility on a 1–5 scale, with 1 = strongly indicates lack of humility "
        "and 5 = strongly indicates humility."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"User's answer: '{user_answer}'\n\n"
        "Please respond ONLY with a single integer from 1 to 5."
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0
    )

    raw_answer = response["choices"][0]["message"]["content"].strip()

    try:
        rating = int(raw_answer)
        if rating < 1 or rating > 5:
            rating = 3  # fallback
    except ValueError:
        rating = 3  # fallback

    return rating

def calculate_final_score(ratings):
    """
    Convert a list of 10 numeric ratings (1–5) into an overall humility
    score (1–10), accounting for reverse-scoring on certain items.
    """
    total_score = 0
    for i, rating in enumerate(ratings):
        if i in REVERSE_SCORED:
            # Invert (1->5, 5->1, etc.)
            rating = 6 - rating
        total_score += rating

    # Now map total_score (10–50) to a scale of 1–10
    final_score = (total_score / 25) * 10
    return round(final_score, 1)

def provide_recommendations(score):
    """
    Provide recommendations based on the final humility score.
    """
    if score <= 3:
        return (
            "You appear to be less open to new information or viewpoints. "
            "Try practicing active listening, asking clarifying questions, "
            "and seeking out mentors who challenge your thinking."
        )
    elif 3 < score <= 6:
        return (
            "You show moderate openness. Consider journaling about situations "
            "where you might have been overly attached to beliefs. Seek more "
            "critical feedback and get comfortable with saying 'I don't know.'"
        )
    elif 6 < score <= 8:
        return (
            "You're fairly intellectually humble. Keep fostering environments "
            "where people feel comfortable challenging you. Stay curious "
            "and open to new ideas."
        )
    else:
        return (
            "You demonstrate high intellectual humility. To maintain this level, "
            "continue challenging yourself with new perspectives, welcoming feedback, "
            "and encouraging others to remain open-minded."
        )

# =========================
# 3) Pushing to GitHub
# =========================
def push_responses_to_github(
    owner: str, 
    repo: str, 
    token: str, 
    file_path: str, 
    content: str, 
    commit_message: str = "Add new responses file"
):
    """
    Pushes a text file to a GitHub repo using the GitHub REST API.
    - `owner`: GitHub username/org
    - `repo`: Repository name
    - `token`: Personal Access Token with 'repo' scope
    - `file_path`: The path in the repo where the file will be created, e.g. "responses/..."
    - `content`: The raw text content to write
    - `commit_message`: The commit message
    """
    # Endpoint to create or update file content:
    # https://api.github.com/repos/{owner}/{repo}/contents/{path}
    url = f"https://api.github.com/repos/{owner}/{repo}/contents/{file_path}"

    # Must base64-encode the content
    encoded_bytes = base64.b64encode(content.encode("utf-8"))
    encoded_str = encoded_bytes.decode("utf-8")

    data = {
        "message": commit_message,
        "content": encoded_str
    }

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    response = requests.put(url, json=data, headers=headers)
    if response.status_code in [200, 201]:
        return True, response.json()
    else:
        return False, response.text

def main():
    st.title("Intellectual Humility Open Ended Questions (GitHub Integration)")

    st.write(
        "Answer five open-ended questions and "
        "we'll compute an intellectual humility score and push your responses to a private GitHub repo."
    )

    # 1) Collect user answers
    user_answers = []
    for i, question in enumerate(QUESTIONS):
        st.write(f"**Question {i+1}:** {question}")
        answer = st.text_area(f"Your answer to Q{i+1}:", key=f"answer_{i}")
        user_answers.append(answer)

    # 2) Button to process
    if st.button("Submit All Answers and Calculate Score"):
        user_ratings = []
        for i, question in enumerate(QUESTIONS):
            answer_text = user_answers[i].strip()
            if not answer_text:
                answer_text = "No answer provided."
            with st.spinner(f"Interpreting your answer for Question {i+1}..."):
                rating = interpret_answer_with_chatgpt(question, answer_text)
            user_ratings.append(rating)

        final_score = calculate_final_score(user_ratings)
        advice = provide_recommendations(final_score)

        st.subheader(f"Your Intellectual Humility Score: {final_score}/10")
        st.write(advice)

        # 3) Build content to push
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"responses_{timestamp}.txt"

        file_content = []
        file_content.append(f"Timestamp: {timestamp}")
        for i, ans in enumerate(user_answers):
            file_content.append(f"Q{i+1}: {QUESTIONS[i]}")
            file_content.append(f"Answer: {ans}")
            file_content.append("")  # blank line
        file_content.append(f"Final Score: {final_score}")
        file_text = "\n".join(file_content)

        # You can choose any subfolder in your repo, e.g. "responses/"
        file_path_in_repo = f"responses/{file_name}"

        st.write("Pushing your responses to GitHub... please wait.")
        success, gh_response = push_responses_to_github(
            owner=GH_OWNER,
            repo=GH_REPO,
            token=GH_TOKEN,
            file_path=file_path_in_repo,
            content=file_text,
            commit_message=f"Add responses file {file_name}"
        )

        if success:
            st.success(f"Successfully pushed your responses to GitHub at {file_path_in_repo}.")
        else:
            st.error(f"Failed to push to GitHub: {gh_response}")

if __name__ == "__main__":
    main()
