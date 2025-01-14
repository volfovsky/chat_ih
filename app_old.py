import openai
import streamlit as st

# Our 10 questions
QUESTIONS = [
    "I enjoy learning from people whose opinions differ from mine.",
    "I find it easy to admit when I’m wrong.",
    "I’m open to revisiting and potentially changing my core beliefs.",
    "I often seek feedback and constructive criticism.",
    "I quickly dismiss opposing viewpoints.",  # reverse scored
    "I find it difficult to say 'I don’t know.'",  # reverse scored
    "I value expertise in areas where I’m not knowledgeable.",
    "I try to see issues from multiple perspectives.",
    "It is important to me to be right, even if evidence suggests otherwise.",  # reverse scored
    "I regularly reflect on how my beliefs may be biased or incomplete."
]

REVERSE_SCORED = [4, 5, 8]  # 0-based indices for Q5, Q6, Q9

def interpret_answer_with_chatgpt(question, user_answer):
    """
    Use the ChatCompletion API to interpret user's answer on a 1–5 scale
    where 1 = strongly indicates humility, 5 = strongly indicates lack of humility.
    """
    system_message = (
        "You are a helpful assistant. You will be given a question about intellectual humility "
        "and the user's answer. Your task: interpret how the user’s answer reflects "
        "their intellectual humility on a 1–5 scale, with 1 = strongly indicates humility "
        "and 5 = strongly indicates lack of humility."
    )
    user_prompt = (
        f"Question: {question}\n"
        f"User's answer: '{user_answer}'\n\n"
        f"Please respond ONLY with a single integer from 1 to 5 that best fits the user's answer."
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
    except:
        rating = 3  # fallback

    return rating

def calculate_final_score(ratings):
    """
    Convert a list of 10 numeric ratings (1–5) into an overall humility
    score of 1–10, accounting for reverse-scoring on certain items.
    """
    total_score = 0
    for i, rating in enumerate(ratings):
        if i in REVERSE_SCORED:
            rating = 6 - rating  # invert for reverse-scored
        total_score += rating

    # Map total_score (10–50) to a final scale of 1–10
    final_score = (total_score / 50) * 10
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
            "critical feedback and learn to embrace 'I don't know.'"
        )
    elif 6 < score <= 8:
        return (
            "You're fairly intellectually humble. Keep fostering environments "
            "where people feel comfortable challenging your ideas. Stay curious "
            "and open to new ideas."
        )
    else:  # score > 8
        return (
            "You demonstrate high intellectual humility. To maintain this level, "
            "continue challenging yourself with new perspectives, welcoming feedback, "
            "and guiding others to remain open-minded."
        )

def main():
    st.title("Intellectual Humility Chatbot")

    st.write("This chatbot will ask you 10 open-ended questions about intellectual humility.")
    st.write("Answer each question in a sentence or two, then click **Submit** for each.")

    # We’ll store answers in a list
    user_answers = []
    for i, question in enumerate(QUESTIONS):
        st.write(f"**Question {i+1}:** {question}")
        user_input = st.text_area(f"Your answer to Q{i+1}:", key=f"answer_{i}")

    # Only proceed once user hits a button
    if st.button("Submit All Answers and Calculate Score"):
        # For each question, interpret the response with ChatGPT
        user_ratings = []
        for i, question in enumerate(QUESTIONS):
            user_input = st.session_state[f"answer_{i}"]  # retrieve the text
            if not user_input.strip():
                # If any answer is blank, give a default rating
                user_input = "No answer provided."
            with st.spinner(f"Interpreting answer for Question {i+1}..."):
                rating = interpret_answer_with_chatgpt(question, user_input)
            user_ratings.append(rating)

        # Calculate final humility score
        final_score = calculate_final_score(user_ratings)
        advice = provide_recommendations(final_score)

        st.subheader(f"Your Intellectual Humility Score: {final_score}/10")
        st.write(advice)

# Set the API key from Streamlit secrets
openai.api_key = st.secrets["OPENAI_API_KEY"]

if __name__ == "__main__":
    main()
