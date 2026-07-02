from flask import Flask, render_template, request
import tensorflow as tf
from tensorflow.keras.preprocessing import image
import numpy as np
import os

app = Flask(__name__)
model = tf.keras.models.load_model('crop_disease_model.h5')

# Define your classes (this should match your model's training labels)
CLASSES = ['Apple_Scab', 'Potato_Early_Blight', 'Tomato_Healthy', 'Corn_Common_Rust', ...]

def predict_disease(img_path):
    img = image.load_img(img_path, target_size=(224, 224))
    img_array = image.img_to_array(img) / 255.0
    img_array = np.expand_dims(img_array, axis=0)
    prediction = model.predict(img_array)
    return CLASSES[np.argmax(prediction)]

@app.route("/", methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['image']
        if file:
            filepath = os.path.join('uploads', file.filename)
            file.save(filepath)
            disease = predict_disease(filepath)
            
            # Logic for harvesting advice
            advice = get_harvesting_tips(disease)
            
            return render_template("result.html", disease=disease, advice=advice)
    return render_template("index.html")

def get_harvesting_tips(disease_name):
    # This acts as your "Harvesting Knowledge Base"
    tips = {
        "Potato_Early_Blight": "Harvest early to prevent tuber infection. Ensure storage is cool (4°C) and dry.",
        "Corn_Common_Rust": "If harvest is near, pick immediately. Ensure corn stalks are dry to prevent further rot.",
        "Healthy": "Optimal harvest is at peak maturity. Check moisture levels (e.g., 13% for Soybeans) for max yield."
    }
    return tips.get(disease_name, "Keep soil aerated and monitor weather for dry harvesting windows.")

if __name__ == "__main__":
    app.run(debug=True)