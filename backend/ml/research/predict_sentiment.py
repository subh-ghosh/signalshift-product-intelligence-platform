import joblib

from text_cleaner import clean_text


# Load trained model
model = joblib.load("../../models/sentiment_model.joblib")

vectorizer = joblib.load("../../models/tfidf_vectorizer.joblib")

print("Model and vectorizer loaded.")


def predict_sentiment(review: str):

    cleaned = clean_text(review)

    vector = vectorizer.transform([cleaned])

    prediction = model.predict(vector)[0]

    return prediction


if __name__ == "__main__":

    test_reviews = [
        "This update is amazing, everything works perfectly",
        "App crashes every time I open it",
        "Login takes forever and the app is very slow",
        "Great design and smooth performance",
        "Worst update ever, nothing works"
    ]

    for review in test_reviews:

        sentiment = predict_sentiment(review)

        print("\nReview:", review)
        print("Predicted Sentiment:", sentiment)