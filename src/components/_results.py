import streamlit as st
import random

st.set_page_config(page_title="Results", page_icon="📊")


def results():
    st.title("Assessment Results")
    st.write(
        "Based on your inputs, here are the likelihoods of being infected with each disease:"
    )

    # Mock disease likelihoods (replace with actual logic)
    # This should be fetched from database
    diseases = {
        "Influenza": random.uniform(0, 50),
        "COVID-19": random.uniform(0, 50),
        "Common Cold": random.uniform(0, 50),
        "Pneumonia": random.uniform(0, 50),
        "Malaria": random.uniform(0, 50),
    }

    # Normalize percentages
    total = sum(diseases.values())
    normalized = {k: (v / total) * 100 for k, v in diseases.items()}
    display_results_as_cards(normalized)


# Display results in card form
def display_results_as_cards(normalized):
    # ("disease": 12)
    sortedList = sorted(normalized.items(), key=lambda item: item[1], reverse=True)
    print(sortedList)
    for disease, likelihood in sortedList:
        # Determine the color based on the likelihood
        color = "#ff4d4d" if likelihood > 20 else "#333"  # Red for >20%, Gray otherwise

        st.markdown(
            f"""
            <div style="
                background-color: #f9f9f9; 
                padding: 20px; 
                margin: 10px 0; 
                border-radius: 8px; 
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); 
                display: flex; 
                justify-content: space-between;
                align-items: center;
            ">
                <div style="font-size: 18px; font-weight: bold; color: #333;">
                    {disease}
                </div>
                <div style="font-size: 18px; font-weight: bold; color: {color};">
                    {likelihood:.2f}%
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


# Display the cards
st.title("Disease Likelihood Results")

if st.button("Back to Home"):
    st.session_state.current_page = "home"
