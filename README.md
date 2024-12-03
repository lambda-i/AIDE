# **AI Disease Evaluator**

The **AI Disease Evaluator** is an interactive web application that helps users assess the likelihood of being affected by various diseases based on their inputs. The app uses OpenAI's GPT-4 for natural language interaction and provides visually appealing results to help users make informed decisions.

---

## **Features**

- **Interactive Chat Interface**:
  - Users can describe their symptoms and medical history using an AI-powered chat.
  - Responses are generated in real-time using OpenAI's GPT-4 API.
- **Disease Likelihood Assessment**:

  - The application calculates the likelihood of various diseases based on user inputs.
  - Results are displayed in dynamic, visually appealing cards.

- **Session Persistence**:
  - Conversation history is maintained throughout the session to provide contextually accurate responses.

---

## **Installation**

### **1. Prerequisites**

- Python 3.8 or higher
- OpenAI API Key (available from [OpenAI](https://platform.openai.com/))

### **2. Clone the Repository**

```bash
git clone <repository-url>
cd <repository-directory>
```

### **3. Set Up a Virtual Environment**

```bash
python -m venv myvenv
source myvenv/bin/activate  # On Windows: myvenv\Scripts\activate
```

### **4. Install Dependencies**

```bash
pip install -r requirements.txt
```

### **5. Configure Environment Variables**

Create a `.env` file in the root directory and copy over all keys from `.env.local.dist` over and replace the placeholder keys with real api keys:

```env
OPENAI_API_KEY=your_openai_api_key_here
```

---

## **Running the Application**

Start the Streamlit server:

```bash
streamlit run src/App.py
```

Open your browser and navigate to the URL displayed in the terminal (usually `http://localhost:8501`).

---

## **Directory Structure**

```
AI Disease Evaluator/
├── src/
│   ├── App.py               # Main entry point of the application
│   ├── components/          # All components used in the frontend
│   ├── pages/               # All pages shown on frontend
│   ├── utils/               # Utilities (i.e. file parsers, validators)
├── requirements.txt         # Dependencies for the project
├── .env                     # Environment variables
├── .env.local.dist          # API key variables to maintain consistency
├── README.md                # Project documentation
```

---

## **Usage**

### **1. Home Page**

- Provides an overview of the application.
- Users can navigate to the Assessment page to start their evaluation.

### **2. Assessment Page**

- Interactive chat interface to describe symptoms, medical history, and other relevant information.
- Powered by OpenAI's GPT-4 for generating contextually relevant responses.

### **3. Results Page**

- Displays the likelihood of diseases in visually appealing cards.
- Cards are conditionally styled based on the likelihood percentage:
  - **Red** for higher scores (>20%)
  - **Gray** for lower scores (≤20%)

---

## **Technologies Used**

- **[Streamlit](https://streamlit.io/)**: Interactive UI and application framework.
- **[OpenAI GPT-4](https://openai.com/)**: Natural language understanding and generation.
- **[Python](https://www.python.org/)**: Core programming language.
- **[HTML/CSS](https://developer.mozilla.org/en-US/docs/Web/HTML)**: For custom card design.
