from flask import Flask, render_template, request
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import euclidean_distances
import numpy as np

app = Flask(__name__)

# Load preprocessed data
data_file = "E:/DATA/PythonProgram/SR/destinasi-wisata-indonesia-preprocessed.xlsx"
data = pd.read_excel(data_file)

# Ensure numeric columns like 'Price' are correctly formatted
data['Price'] = pd.to_numeric(data['Price'], errors='coerce')
data['Rating'] = pd.to_numeric(data['Rating'], errors='coerce')

# Initialize TfidfVectorizer
vectorizer = TfidfVectorizer()

@app.route('/')
def home():
    cities = data['City'].unique() if 'City' in data.columns else []
    categories = data['Category'].unique() if 'Category' in data.columns else []
    return render_template('index.html', cities=cities, categories=categories)

@app.route('/recommend', methods=['POST'])
def recommend():
    city = request.form.get('city')
    category = request.form.get('category')
    max_price = float(request.form.get('price', 0))
    description = request.form.get('description', '')

    # Filter based on city, category, and price
    filtered_data = data[
        (data['City'] == city) & 
        (data['Category'] == category) & 
        (data['Price'] <= max_price)
    ]

    # Preprocess user description
    processed_description = preprocess_text(description)

    if not filtered_data.empty and 'Processed_Description' in filtered_data.columns:
        # Text Similarity
        tfidf_matrix = vectorizer.fit_transform(
            [processed_description] + filtered_data['Processed_Description'].tolist()
        )
        text_similarities = 1 / (1 + euclidean_distances(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten())

        # Price Similarity (normalized)
        if 'Price' in filtered_data.columns and not filtered_data.empty:
            max_price_in_data = filtered_data['Price'].max()
            if max_price_in_data > 0:
                filtered_data['Price_Similarity'] = 1 - (filtered_data['Price'] / max_price_in_data)
            else:
                filtered_data['Price_Similarity'] = 0.0  # Default if no valid price data
        else:
            filtered_data['Price_Similarity'] = 0.0  # Default if no Price column

        # Normalize Rating if it exists
        if 'Rating' in filtered_data.columns:
            max_rating = filtered_data['Rating'].max()
            filtered_data['Normalized_Rating'] = filtered_data['Rating'].fillna(0) / max_rating
        else:
            filtered_data['Normalized_Rating'] = 0.0  # Default if no Rating column

        # Compute final score
        w1, w2, w3, w4 = 0.4, 0.3, 0, 0.3  # Weights for Text, Price, Geo, and Rating
        filtered_data['Description_Similarity'] = text_similarities
        filtered_data['Final_Score'] = (
            w1 * filtered_data['Description_Similarity'] +
            w2 * filtered_data['Price_Similarity'] +
            w4 * filtered_data['Normalized_Rating']
        )

        # Sort by Final Score
        recommendations = filtered_data.sort_values(by=['Final_Score'], ascending=False)
    else:
        recommendations = pd.DataFrame()  # Empty recommendations

    # If no recommendations found, show a message
    if recommendations.empty:
        message = "No recommendations found."
    else:
        message = None

    return render_template('result.html', recommendations=recommendations.to_dict('records'), message=message)

def preprocess_text(text):
    """Preprocess input text for comparison."""
    text = text.lower()
    text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
    text = re.sub(r'\s+', ' ', text).strip()  # Remove extra spaces
    return text

if __name__ == '__main__':
    app.run(debug=True)